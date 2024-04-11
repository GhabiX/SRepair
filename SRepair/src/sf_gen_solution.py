import time
import re
import os
import time
import json
import openai 
import argparse
from tqdm import tqdm
from gen_solution_prompt import sf_construct_prompt


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
    pattern = r'Suggestion \d+:.*?(?=Suggestion \d+:|$)'
    solutions = re.findall(pattern, text, re.DOTALL)
    
    cleaned_solutions = []
    for solution in solutions:
        parts = solution.split(':', 1)
        cleaned_solution = parts[1].strip() if len(parts) > 1 else solution.strip()
        cleaned_solutions.append(cleaned_solution)

    return cleaned_solutions


def extract_root_cause(text):
    pattern = r'Root Cause:.*?(?=Suggestion \d+:|$)'
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        root_cause = match.group().split(':', 1)[1].strip()
        return root_cause
    else:
        return None


def get_solutions(sol_info):
    solutions = {}
    for bug_name in tqdm(sol_info.dataset.keys()):
        solutions[bug_name] = {}
        prompt = sf_construct_prompt(sol_info.dataset, bug_name)
        solutions[bug_name]['prompt'] = prompt
        solutions[bug_name]['solutions'] = query_model(prompt, sol_info.sample_size)
    return solutions


def extract_solutions(raw_solution):
    extracted_solutions = {}
    for bug_name in raw_solution:
        extracted_solutions[bug_name] = {}
        solutions = raw_solution[bug_name]['solutions']

        for solution in solutions:
            split_solution_lst = split_solutions(solution)
            curr_root_cause = extract_root_cause(solution)
            if curr_root_cause not in extracted_solutions[bug_name]:
                extracted_solutions[bug_name][curr_root_cause] = split_solution_lst
            extracted_solutions[bug_name][curr_root_cause].extend(split_solution_lst)

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
