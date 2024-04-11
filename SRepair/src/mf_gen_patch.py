import json
import argparse
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from gen_patch_prompt import mf_build_apr_prompt_auto

model_base_path = './Model'
model_path = f'{model_base_path}/ise-uiuc/Magicoder-S-CL-7B'
model_format_prompt = '''Return your fixed function surrounded with ```java\\n```.\n@@ Instruction\n{apr_prompt}\n@@ Response'''


def extract_function(paragraph, function_id):
    lines = paragraph.split('\n')
    index = 0
    start = -1
    lines_content = []
    
    while index < len(lines):
        if function_id.strip() in lines[index] and (
            'Function' in lines[index] or
            'function' in lines[index]
            ):
            start = index
            break  
        index += 1
    if start == -1:
        return ""
    
    index_of_java = start
    while index_of_java < len(lines):
        if '```java' in lines[index_of_java]:
            start = index_of_java + 1
            break
        index_of_java += 1
    if index_of_java == len(lines):
        index_of_java = start
        while index_of_java < len(lines):
            if '```' in lines[index_of_java]:
                start = index_of_java + 1
                break
            index_of_java += 1
    index = start - 1

    while 0 <= index < len(lines):
        line = lines[index].strip()
        if len(line) == 0:
            break
        if line[0] == "@" and not line.startswith("@@") and not line.endswith("*/"):
            lines_content.append(lines[index])
            index -= 1
            continue
        break
    
    lines_content.reverse()
    
    bracket_cnt = 0
    bracket_flag = False

    if start >= len(lines):
        return ''
    
    first_line = lines[start]
    if not (first_line.endswith(';') and first_line.count('{')==0):
        for i in range(start, len(lines)):
            line = lines[i]
            lines_content.append(line)
            bracket_cnt += line.count('{')
            if bracket_cnt:
                bracket_flag = True
            bracket_cnt -= line.count('}')
            if bracket_cnt == 0 and bracket_flag:
                break
    
    return '\n'.join(lines_content)


def extract_patch(dataset, raw_patch_result):
    extracted_patch_result = {}
    for bug_name in raw_patch_result.keys():
        extracted_patch_result[bug_name] = {'prompt': raw_patch_result[bug_name]['prompt'], 'patches': []}
        for raw_patch in raw_patch_result[bug_name]['patches']:
            if raw_patch.startswith(':'):
                raw_patch = raw_patch[1:]
            elif raw_patch.startswith('@@ Response:'):
                raw_patch = raw_patch[12:]
            extracted_patch = {}
            for function_id in range(1, len(dataset[bug_name]['functions']) + 1):
                extracted_patch[str(function_id)] = extract_function(raw_patch, str(function_id))
                if extracted_patch[str(function_id)] is None:
                    extracted_patch[str(function_id)] = ''
            extracted_patch_result[bug_name]['patches'].append(extracted_patch)
    return extracted_patch_result


class AprInfo():
    def __init__(self, dataset_path, suggestions_path, out_path, target_bug):
        with open(dataset_path, 'r') as f:
            self.dataset = json.load(f)
        with open(suggestions_path, 'r') as f:
            self.suggestions = json.load(f)
        if target_bug is not None:
            self.dataset = {target_bug: self.dataset[target_bug]}
            self.suggestions = {target_bug: self.suggestions[target_bug]}
        self.out_path = out_path
        self.target_bug = target_bug
        return


def opensrc_model_apr(apr_info):
    dataset = apr_info.dataset
    suggestions = apr_info.suggestions
    
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True, torch_dtype=torch.float16)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)

    patches = {}
    for bug_name in dataset:
        buggy_function_total = []
        for buggy_function in apr_info.dataset[bug_name]['functions']:
            buggy_function_total.append(buggy_function['buggy_function'])
        buggy_function_total = '\n'.join(buggy_function_total)
        curr_max_new_token = max(256, 2*len(tokenizer.encode(buggy_function_total)))

        curr_patch = {}
        curr_patch['prompt'] = []
        curr_patch['patches'] = []

        for suggestion in suggestions[bug_name]:
            apr_prompt = mf_build_apr_prompt_auto(dataset[bug_name], suggestion['root_cause'], suggestion['solution'])
            prompt = model_format_prompt.format(apr_prompt=apr_prompt.strip())
            prompt_token_len = len(tokenizer.encode(prompt))
            if prompt_token_len > 4000:
                continue

            curr_patch['prompt'].append(apr_prompt)
            suggest_patch = []
            batch_size = 5
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            pad_token_id = tokenizer.convert_tokens_to_ids(tokenizer.pad_token)
            inputs = tokenizer(prompt, return_tensors="pt", padding=True).to("cuda") 
            
            while len(suggest_patch) < 5:
                try:
                    outputs = model.generate(
                        inputs["input_ids"],
                        max_new_tokens=curr_max_new_token,
                        attention_mask=inputs["attention_mask"],
                        pad_token_id=pad_token_id,
                        do_sample=True,
                        top_p=0.9,
                        temperature=0.8,
                        num_return_sequences=batch_size,
                    )
                    for _, output in enumerate(outputs):
                        generated_text = tokenizer.decode(output, skip_special_tokens=True)
                        prompt_end_idx = generated_text.find(apr_prompt.strip()) + len(apr_prompt.strip())
                        fixed_result = generated_text[prompt_end_idx:].strip() if prompt_end_idx != -1 else generated_text
                        fixed_result = fixed_result.replace('[/INST]  ','')
                        suggest_patch.append(fixed_result)

                    curr_patch_cnt = len(curr_patch['patches']) + len(suggest_patch)
                    print(f'### [APR]:bug_name:{bug_name:25}  |  curr_patch_cnt:{curr_patch_cnt:>3}  |  batch_size:{batch_size:2}  |  patches_cnt:{len(patches):3} ###')

                except RuntimeError as e:
                    if 'out of memory' in str(e):
                        batch_size = batch_size//2
                        if batch_size == 0:
                            break
                    else:
                        raise e
            curr_patch['patches'].extend(suggest_patch)
        patches[bug_name] = curr_patch

    return patches


def main():
    apr_result = {}
    apr_info = AprInfo(
        args.d,
        args.s,
        args.o,
        args.bug
    )
    apr_result = opensrc_model_apr(apr_info)
    apr_result = extract_patch(apr_info.dataset, apr_result)
    with open(apr_info.out_path, 'w') as f:
        json.dump(apr_result, f, indent=2)
    return
    
def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', type=str, required=True, help='dataset path')
    parser.add_argument('-s', type=str, required=True, help='suggestions path')
    parser.add_argument('-o', type=str, required=True, help='patch_result path')
    parser.add_argument('-bug', type=str, required=False, help='bug')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    main()
