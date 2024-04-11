import os
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_NAME = "ise-uiuc/Magicoder-S-CL-7B"
# MODEL_NAME = "codellama/CodeLlama-7b-Instruct-hf"
# MODEL_NAME = "codellama/CodeLlama-13b-Instruct-hf"
# MODEL_NAME = "codellama/CodeLlama-34b-Instruct-hf"

DUMP_PATH = './Model/'
if __name__ == '__main__':
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    tokenizer.save_pretrained(DUMP_PATH + MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, force_download=True)
    model.save_pretrained(DUMP_PATH + MODEL_NAME)