import time
import re
import os
import time
import json
import openai
import argparse
from tqdm import tqdm
from gen_solution_prompt import mf_construct_prompt


def query_model(prompt, sample_size):
    os.environ["OPENAI_API_KEY"] = 'OPENAI_API'
    delay = 10
    while(True):
        try:
            response = api_gpt3_5_response(prompt, sample_size)
            break
        except openai.APIError as e:
            if "Please reduce " in str(e):
                raise ValueError("Over Length")
            print(f"OpenAI API returned an API Error: {e}")
            time.sleep(delay)
        except Exception as e:
            print(f"Exception in api_query_model {e}")
            if "Please reduce " in str(e):
                raise ValueError("Over Length")
            time.sleep(delay)

    response_list = []
    for choice in response.choices:
        if choice.message:
            response_list.append(choice.message.content)
    return response_list


def api_gpt3_5_response(prompt, n):
    response = openai.chat.completions.create(    
        messages=[{"role": "user", "content": prompt}],
        model="gpt-3.5-turbo-1106",
        n=n,
        temperature=0.8)
    return response


class SolInfo():
    def __init__(self, dataset_path, solution_path, extracted_solution_path, sample_size, target_bug):
        with open(dataset_path, 'r') as f:
            self.dataset = json.load(f)
        if target_bug is not None:
            self.dataset = {target_bug: self.dataset[target_bug]}
        self.solution_path = solution_path
        if extracted_solution_path is None:
            exp_name_idx = len(solution_path) - 1
            while exp_name_idx >= 0 and solution_path[exp_name_idx] != '.':
                exp_name_idx -= 1
            if exp_name_idx >= 0:
                self.extracted_solution_path = solution_path[: exp_name_idx] + '_extracted' + solution_path[exp_name_idx:]
            else:
                self.extracted_solution_path = solution_path + '_extracted.json'
        else:
            self.extracted_solution_path = extracted_solution_path
        self.sample_size = sample_size
        self.target_bug = target_bug
        return


def split_solutions(text):
    pattern = r"Function ID:(.+?)\nSuggestion:\n(.+?)(?=Function ID:|$)"
    matches = re.findall(pattern, text,flags=re.DOTALL)
    function_suggestions={}
    for match in matches:
        function_suggestions[match[0].strip()]=match[1].strip().strip('\n')
    return function_suggestions


def extract_root_cause(text):
    pattern = r'Root Cause:.*?(?=Suggestions:|Function ID:|$)'
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        root_cause = match.group().split(':', 1)[1].strip().strip('\n')
        return root_cause
    else:
        return None


def get_solutions(sol_info):
    solutions = {}
    for bug_name in tqdm(sol_info.dataset.keys()):
        solutions[bug_name] = {}
        prompt = mf_construct_prompt(sol_info.dataset, bug_name)
        solutions[bug_name]['prompt'] = prompt
        solutions[bug_name]['solutions'] = query_model(prompt, sol_info.sample_size)
    return solutions


def extract_solutions(raw_solution):
    extracted_solutions = {}
    for bug_name in raw_solution:
        extracted_solutions[bug_name] = []
        curr_raw_solution = raw_solution[bug_name]
        solutions = curr_raw_solution['solutions']

        for solution in solutions:
            split_solution_dic = split_solutions(solution)
            curr_root_cause = extract_root_cause(solution)
            this_extracted_solution = {'solution': split_solution_dic, 'root_cause': curr_root_cause}
            extracted_solutions[bug_name].append(this_extracted_solution)

    return extracted_solutions


def main():
    sol_info = SolInfo(
        args.d,
        args.o,
        args.eo,
        args.s,
        args.bug
    )
    solutions = get_solutions(sol_info)
    with open(sol_info.solution_path, 'w') as f:
        json.dump(solutions, f, indent=2)
    extracted_solutions = extract_solutions(solutions)
    with open(sol_info.extracted_solution_path, 'w') as f:
        json.dump(extracted_solutions, f, indent=2)
    return 


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', type=str, required=True, help='dataset path')
    parser.add_argument('-o', type=str, required=True, help='raw_solution path')
    parser.add_argument('-eo', type=str, required=False, help='extracted_solution path')
    parser.add_argument('-s', type=int, required=False, help='sample_size', default=1)
    parser.add_argument('-bug', type=str, required=False, help='bug')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    main()
