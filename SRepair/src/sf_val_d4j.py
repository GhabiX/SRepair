import os
import sys
import time
import json
import shutil
import random
import psutil
import argparse
import threading
import traceback
import subprocess
import multiprocessing
from pathlib import Path
import concurrent.futures as cf
from contextlib import contextmanager, redirect_stdout, redirect_stderr



def clean_tmp_folder(tmp_dir):
    if os.path.isdir(tmp_dir) and tmp_dir.startswith('/tmp/'):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir)


def strip_lines(lines):
    return [line.strip() for line in lines]


def encoding_check(encoding_check_file_path):
    file_content = None
    encoding_mode = 'utf-8'
    try:
        with open(encoding_check_file_path, 'r', encoding=encoding_mode) as f:
            file_content = f.read()
    except UnicodeDecodeError:
        encoding_mode = 'ISO-8859-1'
        with open(encoding_check_file_path, 'r', encoding=encoding_mode) as f:
            file_content = f.read()
    except Exception as e:
        print(f"[ERROR] read encoding_check FAILURE: {e}")
        return None
    return encoding_mode, file_content


def checkout_defects4j_project(current_bug, project_dir):
    project, bug_id = current_bug.split('-')
    FNULL = open(os.devnull, 'w')
    command = "defects4j checkout " + " -p " + project + " -v " + bug_id + 'b'  + " -w " + project_dir
    print('[CHECKOUT]', command)
    p = subprocess.Popen([command], shell=True, stdout=FNULL, stderr=FNULL)
    p.wait()
    return


def monitor_memory(pid, interval, stop_event, max_memory_event):
    max_memory = 0
    try:
        main_proc = psutil.Process(pid)
        while not stop_event.is_set():
            procs = [main_proc] + main_proc.children(recursive=True)
            total_memory_usage = sum(proc.memory_info().rss for proc in procs if proc.is_running())
            max_memory = max(max_memory, total_memory_usage)
            time.sleep(interval)
    except psutil.NoSuchProcess:
        pass
    max_memory_event[0] = max_memory / (1024 ** 3)


def command_with_timeout(cmd, timeout=90):
    max_memory_event = [None]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stop_event = threading.Event()
    monitor_thread = threading.Thread(target=monitor_memory, args=(process.pid, 1, stop_event, max_memory_event))
    try:
        monitor_thread.start()
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        ps_process = psutil.Process(process.pid)
        procs_kill = [ps_process] + ps_process.children(recursive=True)
        for proc in procs_kill:
            proc.kill()
        return 'TIMEOUT', 'TIMEOUT'
    finally:
        stop_event.set()
        monitor_thread.join()
        max_memory_usage = max_memory_event[0]
        if max_memory_usage and max_memory_usage > 6:
            print(f'[WARNING] MEMORY OCCUPIED {max_memory_usage:.2f} GB -- {cmd}')
    return stdout, stderr


def defects4j_test_suite(project_dir, timeout=1000):
    os.chdir(project_dir)
    out, err = command_with_timeout(["defects4j", "test", "-r"], timeout)
    if "Compilation failed" in str(out):
        print("[FAIL] Compile tests for ", project_dir)
    return out, err


def defects4j_export_trigger(project_dir, timeout=90):
    os.chdir(project_dir)
    out, err = command_with_timeout(["defects4j", "export", "-p", "tests.trigger"], timeout)
    return out, err


def defects4j_export_relevant(project_dir, timeout=90):
    os.chdir(project_dir)
    out, err = command_with_timeout(["defects4j", "export", "-p", "tests.relevant"], timeout)
    return out, err


def defects4j_test_one(project_dir, test_case, timeout=100):
    os.chdir(project_dir)
    out, err = command_with_timeout(["defects4j", "test", "-t", test_case], timeout)
    return out, err


def extract_d4j_result(err, out, val_stage):
    err_str, out_str = str(err), str(out)
    if 'TIMEOUT' in err_str or 'TIMEOUT' in out_str:
        correctness = 'TRIGGER_TIMEOUT' if val_stage == 'trigger' else 'RELEVANT_TIMEOUT'
    elif 'FAIL' in err_str or 'FAIL' in out_str:
        correctness = 'UNCOMPILABLE'
    elif "Failing tests: 0" in out_str:
        correctness = 'PLAUSIBLE'
    else:
        correctness = 'TRIGGER_ERROR' if val_stage == 'trigger' else 'RELEVANT_ERROR'
    return correctness




class ValTime:
    def __init__(self, val_start_time):
        self.val_start_timestamp = val_start_time
        
        self.val_init_time = 0
        self.val_overall_time = 0

        self.val_trigger_time = 0
        self.curr_trigger_time = 0
        self.trigger_start_timestamp = 0

        self.val_relevant_time = 0
        self.curr_relevant_time = 0
        self.relevant_start_timestamp = 0

        self.curr_overall_time = 0

    def set_init_time(self, init_timestamp):
        self.val_init_time = init_timestamp - self.val_start_timestamp

    def set_trigger_start_timestamp(self, trigger_start_timestamp):
        self.trigger_start_timestamp = trigger_start_timestamp
    
    def set_relevant_start_timestamp(self, relevant_start_timestamp):
        self.relevant_start_timestamp = relevant_start_timestamp

    def set_trigger_end_time(self, trigger_end_timestamp):
        self.curr_trigger_time = trigger_end_timestamp - self.trigger_start_timestamp
        self.val_trigger_time += self.curr_trigger_time
    
    def set_relevant_end_time(self, relevant_end_timestamp):
        self.curr_relevant_time = relevant_end_timestamp - self.relevant_start_timestamp
        self.val_relevant_time += self.curr_relevant_time
    
    def get_curr_overall_time(self):
        self.curr_overall_time = self.curr_trigger_time + self.curr_relevant_time
        return int(self.curr_overall_time)
    
    def set_overall_time(self, end_timestamp):
        self.val_overall_time = end_timestamp - self.val_start_timestamp
    
    def get_relevant_time(self):
        return int()
    
    def print_validation_time_info(self, curr_bug):
        print(f"[TIME INFO] PREPARE  = {int(self.val_init_time)}s")
        print(f"[TIME INFO] TRIGGER  = {int(self.val_trigger_time)}s")
        if self.val_relevant_time > 2:
            print(f"[TIME INFO] RELEVANT = {int(self.val_relevant_time)}s")
        print(f'[TIME INFO] TOTAL {curr_bug} -- {int(int(self.val_overall_time))}s')
        print('=' * 100)




class ValInfo():
    def __init__(self, candidate_patch):
        self.unvrf_patches = candidate_patch

        self.patch_id = 0
        self.validated_result = []
        self.overall_patch_status = 'failure'

        self.init_buggy_project()
        self.init_bug_status_info()
        self.init_extract_project_info()


    def init_buggy_project(self):
        self.curr_bug = self.unvrf_patches[0]
        self.patches = self.unvrf_patches[1]['patches']
        random.shuffle(self.patches)
        
        self.validation_path = '/tmp/llm4apr_validation/'
        self.proj_dir = os.path.join(self.validation_path, self.curr_bug)
        clean_tmp_folder(self.proj_dir)
        config_path = os.path.join(self.validation_path, 'config.json')
        with open(config_path, 'r') as f:
            config_info = json.load(f)

        self.val_result_path = config_info['output_path']
        dataset_path = config_info['dataset_path']
        with open(dataset_path, "r") as f:
            self.dataset = json.load(f)
        checkout_defects4j_project(self.curr_bug, self.proj_dir)


    def init_bug_status_info(self):
        time_out = 2000
        init_out, _ = defects4j_test_suite(self.proj_dir, time_out)
        self.failed_test_cases = strip_lines(str(init_out).split(' - ')[1:])
        trigger, _ = defects4j_export_trigger(self.proj_dir)
        self.trigger_tests = strip_lines(trigger.strip().split('\n'))
        relevant, _ = defects4j_export_relevant(self.proj_dir)
        self.relevant_tests = strip_lines(relevant.strip().split('\n'))
        
        
    def init_extract_project_info(self):
        bug_path = self.dataset[self.curr_bug]['loc']
        self.buggy_file_path = os.path.join(self.proj_dir, bug_path)
        self.encoding_mode, self.original_buggy_file_content = encoding_check(self.buggy_file_path)

        self.backup_buggy_file_path = f'{self.buggy_file_path}.llm4apr_backup'
        shutil.copyfile(self.buggy_file_path, self.backup_buggy_file_path)

    
    def check_init_success(self):
        return len(self.failed_test_cases) > 0
    
    
    def patch_id_counter(self):
        self.patch_id += 1


    def update_patch_val_result(self, patch_validation_info):
        self.validated_result.append(patch_validation_info)

    
    def save_validation_results(self, done=False):
        if not done and len(self.validated_result) % 10 != 0:
            return
        filename = str(self.curr_bug) + '-validated.jsonl'
        log_file = os.path.join(self.val_result_path, filename)
        if not os.path.exists(self.val_result_path):
            os.makedirs(self.val_result_path, exist_ok=True)
        try:   
            with open(log_file, "w") as f: 
                json.dump(self.validated_result, f, indent=2)
        except Exception as e:
            print('[ERROR] write_results_to_file: ', e)  



        
class PatchValidation():
    def __init__(self, patch_code):
        self.patch_code = patch_code
        self.patch_status = 'UNVERIFIED'
        self.failing_test = {
            'TRIGGER' : [],
            'RELEVANT' : [],
            'TIMEOUT' : [],
        }
        self.patch_val_info = {}

    def apply_patch(self, bug_info, proj_dir, encoding_mode):
        bug_path = bug_info['loc']
        start_loc = bug_info['start']
        end_loc = bug_info['end']
        patch = self.patch_code.strip()
        buggy_full_path = os.path.join(proj_dir, bug_path)        
        with open(buggy_full_path, 'r', encoding=encoding_mode) as file:
            orig_buggy_code = file.readlines()
        with open(buggy_full_path, 'w', encoding=encoding_mode, errors='ignore') as file:
            patched = False
            for idx, line in enumerate(orig_buggy_code):
                if start_loc - 1 <= idx <= end_loc -1:
                    if not patched:
                        file.write(patch)
                        patched = True
                else:
                    file.write(line)
            assert patched, f'[ERROR] [ASSERT FAILURE] insert_fix_into_src not pateced'
        return

    
    def trigger_test_validation(self, trigger_tests, proj_dir):
        for trigger in trigger_tests:
            if self.patch_status == 'UNVERIFIED' or self.patch_status == 'PLAUSIBLE':
                out, err = defects4j_test_one(proj_dir, trigger)
                self.patch_status = extract_d4j_result(err, out, 'trigger')
                if self.patch_status == 'TRIGGER_ERROR': 
                    self.failing_test['TRIGGER'].append(trigger)
                elif self.patch_status == 'TRIGGER_TIMEOUT':
                    self.failing_test['TIMEOUT'].append(trigger)


    def relevant_test_validation(self, proj_dir):
        if self.patch_status != 'PLAUSIBLE':
            return
        out, err = defects4j_test_suite(proj_dir)
        self.patch_status = extract_d4j_result(err, out, 'relevant')
        self.failing_test['RELEVANT'] = [test_case.strip() for test_case in str(out).split(' - ')[1:]]
    
    
    def print_curr_patch_status(self, curr_bug, curr_overall_time):
        print(f'[PATCH STATUS] | {curr_bug:20} | {self.patch_status:16} | {curr_overall_time:4}s  |')
        
        
    def recover_buggy_file(self, backup_buggy_file_path, orig_file_content, patch_id, encoding_mode, proj_dir):
        if '.llm4apr_backup' not in backup_buggy_file_path:
            print(f'[ERROR] .llm4apr_backup not in backup_file')
            return
        recover_buggy_path = backup_buggy_file_path.replace('.llm4apr_backup', '')
        patched_backup_file_path = f'{recover_buggy_path}_{patch_id}_{self.patch_status}'
        shutil.move(recover_buggy_path, patched_backup_file_path)
        shutil.copyfile(backup_buggy_file_path, recover_buggy_path)
        with open(recover_buggy_path, 'r', encoding=encoding_mode) as f:
            file_content = f.read()
            assert orig_file_content == file_content, f'[ERROR] [ASSERT FAILURE] recover_original_file'
        
        # fix the bug of defects4j project's incremental compilation error in trigger test
        assert proj_dir.startswith('/tmp/llm4apr_validation/'), f'[ERROR] [ASSERT FAILURE] \
                recover_buggy_file FAILURE {proj_dir} NOT TEMP FILE'
        rm_class_filename = os.path.basename(recover_buggy_path).replace('.java', '.class')
        root_dir = Path(proj_dir)
        for file in root_dir.rglob(rm_class_filename):
            file.unlink()
            return

    def summarize_patch_info(self, bug_name):
        self.patch_val_info = {
            'patch_code': self.patch_code, 
            'patch_status': self.patch_status, 
            'failing_tests': self.failing_test,
            'val_cnt' : 1,
            'bug_name' : bug_name
        }
        return self.patch_val_info
        



def validate_patches_per_bug(candidate_patch):
    val_time = ValTime(time.time())
    val_info = ValInfo(candidate_patch)
    if not val_info.check_init_success():
        return
    val_time.set_init_time(time.time())
    for curr_patch_code in val_info.patches:
        val_info.patch_id_counter()
        patch_val = PatchValidation(curr_patch_code)
        patch_val.apply_patch(val_info.dataset[val_info.curr_bug], val_info.proj_dir, val_info.encoding_mode)
        
        val_time.set_trigger_start_timestamp(time.time())
        patch_val.trigger_test_validation(val_info.trigger_tests, val_info.proj_dir)
        val_time.set_trigger_end_time(time.time())

        val_time.set_relevant_start_timestamp(time.time())
        patch_val.relevant_test_validation(val_info.proj_dir)
        val_time.set_relevant_end_time(time.time())    

        patch_val.print_curr_patch_status(val_info.curr_bug, val_time.get_curr_overall_time())
        patch_val.recover_buggy_file(val_info.backup_buggy_file_path, val_info.original_buggy_file_content, \
                                     val_info.patch_id, val_info.encoding_mode, val_info.proj_dir)

        curr_patch_summary = patch_val.summarize_patch_info(val_info.curr_bug)
        val_info.update_patch_val_result(curr_patch_summary)
        val_info.save_validation_results()
    
    val_time.set_overall_time(time.time())
    val_time.print_validation_time_info(val_info.curr_bug)
    val_info.save_validation_results(done=True)
    

def validate_defects4j(candidate_patches):
    workers = int(multiprocessing.cpu_count() / 5)
    with cf.ProcessPoolExecutor(max_workers=workers) as pool:
        future = pool.map(validate_patches_per_bug, candidate_patches.items())
        for result in future:
            try:
                pass 
            except Exception as e:
                print(f"Exception: {repr(e)}")
                traceback.print_exc()
                continue
    print('[END VALIDATION]')
    sys.stdout.flush()
    time.sleep(3)
    return

@contextmanager
def log_or_print(log_mode, log_path):
    if log_mode:
        with open(log_path, 'a') as log_file, redirect_stdout(log_file), redirect_stderr(log_file):
            yield
    else:
        yield

def shuffle_validated_patches(candidate_patches):
    items = list(candidate_patches.items())
    random.shuffle(items)
    shuffled_patches = {key: value for key, value in items}
    return shuffled_patches


if __name__ == '__main__':
    start_val_time = time.time()

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', type=str, required=True, help='patch file path')
    parser.add_argument('-o', type=str, required=False, help='validation result output path(Empty Dir)', \
                        default='/tmp/llm4apr_validation/result')
    parser.add_argument('-d', type=str, required=False, help='validation dataset path')
    parser.add_argument('-log', action='store_true', help='log mode(std-o/e to validation.log).')
    args = parser.parse_args()
    
    validation_config = {
        'input_path'    : os.path.abspath(args.i),
        'output_path'   : os.path.abspath(args.o),
        'dataset_path'  : os.path.abspath(args.d),
        'log_mode'      : args.log,
    }
    input_patch_file =  os.path.abspath(args.i)
    output_result_dir =  os.path.abspath(args.o)

    validation_tmp_path = '/tmp/llm4apr_validation/'
    validation_config_path = '/tmp/llm4apr_validation/config.json'
    log_file_path = os.path.join(os.path.abspath(args.o), 'validation.log')

    clean_tmp_folder(validation_tmp_path)
    with open(validation_config_path, 'w') as f:
        json.dump(validation_config, f, indent=2)

    assert not os.path.exists(output_result_dir) or (os.path.isdir(output_result_dir) and len(os.listdir(output_result_dir)) == 0), \
        f"[ERROR] [ASSERT FAILURE] {output_result_dir} should either not exist or be an empty directory."
    
    candidate_patches = json.load(open(input_patch_file, 'r'))
    candidate_patches = shuffle_validated_patches(candidate_patches)

    os.makedirs(output_result_dir)
    with log_or_print(log_mode=args.log, log_path=log_file_path):
        validate_defects4j(candidate_patches)
        print(f'[TIME INFO] total_time = {int(time.time() - start_val_time)} s')