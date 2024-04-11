FROM ubuntu:20.04

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y vim git zsh wget curl file htop screen openjdk-8-jdk \
    software-properties-common ant python3 python3-pip build-essential subversion perl unzip cpanminus make && \
    apt-get clean


ENV JAVA_HOME /usr/lib/jvm/java-8-openjdk-amd64/

WORKDIR /

RUN git clone https://github.com/rjust/defects4j.git defects4j && \
    cd /defects4j && \
    cpanm --installdeps . && \
    ./init.sh

ENV PATH="/defects4j/framework/bin:${PATH}"  

RUN pip install psutil tqdm tiktoken openai && \
    pip install git+https://github.com/huggingface/transformers.git@main


ADD ./ /data/LLM4APR

ENTRYPOINT ["/bin/bash"]