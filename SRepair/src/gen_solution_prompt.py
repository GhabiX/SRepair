import random
import tiktoken


mf_start_assist_prompt = '''
This bug consists of multiple interdependent buggy functions, meaning that fix should be achieved by simultaneously modifying these functions. You need to first analyse the buggy code, trigger test and error message. Then analyse the root cause and finally try to provide a repair suggestions to fix the bug.
Note that the bug can be fixed by modifying only the given buggy code; do not attempt to modify the class, add new functions, or conduct further testing.'''
mf_end_assist_prompt = '''
First, analyze the trigger test and error message, and then analyse the root cause of this bug in the format 'Root Cause:\\n{content}'. Then provide detailed patch suggestion for each buggy function to resolve this bug.
You suggestions should be in the format 'Function ID: {ID}\\nSuggestion:\\n{content}', etc.'''


sf_start_assist_prompt = '''
You need to first analyse the buggy code, trigger test and error message. Then analyse the root cause and finally try to provide a repair suggestions to fix the buggy.
Note that the bug can be fixed by modifying only the given buggy code; do not attempt to modify the class, add new functions, or conduct further testing.'''
sf_end_assist_prompt = '''
First, analyze the trigger test and error message, and then analyse the root cause of the buggy function in the format 'Root Cause: {content}'. Provide multiple distinct and detailed patch suggestions for resolving this bug.
You suggestions should be in the format 'Suggestion 1: {suggestion title}\\n{detailed description}', etc.'''


def sf_construct_prompt(dataset, bug_name):
    random_trigger_test = random.choice(list(dataset[bug_name]['trigger_test'].keys()))
    err_msg = dataset[bug_name]['trigger_test'][random_trigger_test]['clean_error_msg']
    err_msg = slim_content_token(err_msg)
    trigger_src = dataset[bug_name]['trigger_test'][random_trigger_test]['src']

    comment = dataset[bug_name]['buggy_code_comment']
    buggy_function = dataset[bug_name]['buggy']
    
    curr_prompt_lst = []
    curr_prompt_lst.append(sf_start_assist_prompt)
    curr_prompt_lst.append(f'\n1. Buggy Function: \n{comment}\n{buggy_function}')
    curr_prompt_lst.append(f'\n2. Trigger Test: \n{trigger_src}')
    curr_prompt_lst.append(f'\n3. Error Message: \n{err_msg}\n')
    curr_prompt_lst.append(sf_end_assist_prompt) 
    curr_prompt = '\n'.join(curr_prompt_lst)
    return curr_prompt


def mf_construct_prompt(dataset, bug_name):
    random_trigger_test = random.choice(list(dataset[bug_name]['trigger_test'].keys()))
    err_msg = dataset[bug_name]['trigger_test'][random_trigger_test]['clean_error_msg']
    err_msg = slim_content_token(err_msg)
    trigger_src = dataset[bug_name]['trigger_test'][random_trigger_test]['src']
    
    curr_prompt_lst = []
    curr_prompt_lst.append(mf_start_assist_prompt)
    curr_prompt_lst.append(f'\n1. Buggy Function: ')
    function_id = 1
    for function in dataset[bug_name]['functions']:
        comment = function['comment']
        buggy_function = function['buggy_function']
        curr_prompt_lst.append(f'\nFunction ID: {function_id}\n{comment}{buggy_function}')
        function_id += 1
    curr_prompt_lst.append(f'\n2. Trigger Test: \n{trigger_src}')
    curr_prompt_lst.append(f'\n3. Error Message: \n{err_msg}\n')
    curr_prompt_lst.append(mf_end_assist_prompt)
    curr_prompt = '\n'.join(curr_prompt_lst)
    return curr_prompt


def slim_content_token(err_msg):
    token_upper_limit = 200
    err_msg_lst = err_msg.split('\n')
    slim_err_msg_lst = []
    for line in err_msg_lst:
        curr_line_token_cnt = num_tokens_from_string(line)
        token_upper_limit -= curr_line_token_cnt
        if token_upper_limit <= 0:
            break
        slim_err_msg_lst.append(line)
    return '\n'.join(slim_err_msg_lst)


def num_tokens_from_string(string: str) -> int:
    encoding_name = "cl100k_base"
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens
