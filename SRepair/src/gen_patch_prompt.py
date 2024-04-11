apr_label = '// Provide a fix for the buggy function.'
buggy_label = '// Buggy Function'
fixed_label = '// Fixed Function'

mf_start_prompt = 'This bug consists of multiple interdependent buggy functions, meaning that fix should be achieved by simultaneously modifying these functions.'
mf_end_prompt = 'Povide fixed function for each buggy functions. Your output should be strictly in the format \'Function ID: {ID}\\nFixed function code:\\n{fixed function code}\' without any other content'


def sf_build_apr_prompt_auto(buggy_function, root_cause, suggestion):
    parts = []
    parts.append(apr_label)
    parts.append('Root cause: ' + root_cause)
    parts.append('Suggestion: ' + suggestion)
    parts.append(buggy_label)
    parts.append(buggy_function)
    parts.append(fixed_label)
    return '\n'.join(parts)


def mf_build_apr_prompt_auto(bug_info, root_cause, suggestions):
    parts = []
    parts.append(mf_start_prompt)
    parts.append('Root cause: ' + root_cause)
    parts.append(buggy_label)
    for function_id in suggestions.keys():
        parts.append('Function ID: ' + function_id)
        parts.append('Fix suggestion: ' + suggestions[function_id])
        parts.append(bug_info['functions'][int(function_id) - 1]['buggy_function'])
        parts.append('\n')
    parts.append(mf_end_prompt)
    return '\n'.join(parts)