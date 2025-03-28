import os
import sys
import re

def execute_command(tokens, background, input_file, output_file):
    if not tokens:
        return

    if tokens[0] == "exit":
        sys.exit(0)

    if tokens[0] == "cd":
        try:
            os.chdir(tokens[1] if len(tokens) > 1 else os.getenv("HOME"))
        except FileNotFoundError:
            os.write(2, f"cd: no such file or directory: {tokens[1]}\n".encode())
        return

    rc = os.fork()
    if rc < 0:
        os.write(2, b"Fork failed\n")
        sys.exit(1)
    elif rc == 0:  # Child process
        if input_file:
            os.close(0)
            os.open(input_file, os.O_RDONLY)
        if output_file:
            os.close(1)
            os.open(output_file, os.O_CREAT | os.O_WRONLY)
        try:
            os.execvp(tokens[0], tokens)
        except FileNotFoundError:
            os.write(2, f"{tokens[0]}: command not found\n".encode())
            sys.exit(1)
    else:  # Parent process
        if not background:
            pid, status = os.wait()
            if os.WIFEXITED(status) and os.WEXITSTATUS(status) != 0:
                os.write(2, f"Program terminated with exit code {os.WEXITSTATUS(status)}\n".encode())


def parse_command(command):
    background = "&" in command
    command = command.replace("&", "")
    input_file = output_file = None
    tokens = command.split()

    if "<" in tokens:
        idx = tokens.index("<")
        if idx + 1 < len(tokens):
            input_file = tokens[idx + 1]
        tokens = tokens[:idx]

    if ">" in tokens:
        idx = tokens.index(">")
        if idx + 1 < len(tokens):
            output_file = tokens[idx + 1]
        tokens = tokens[:idx]

    return tokens, background, input_file, output_file

def execute_pipeline(commands):
    processes = []
    pipes = []

    for i in range(len(commands) - 1):
        pr, pw = os.pipe()
        pipes.append((pr, pw))

    for i, command in enumerate(commands):
        tokens, background, input_file, output_file = parse_command(command)
        rc = os.fork()
        if rc == 0:  # Child process
            if i > 0: 
                os.dup2(pipes[i - 1][0], 0)
            if i < len(commands) - 1:  
                os.dup2(pipes[i][1], 1)
            for pr, pw in pipes:
                os.close(pr)
                os.close(pw)
            execute_command(tokens, background, input_file, output_file)
            sys.exit(1)
        else:
            processes.append(rc)

    for pr, pw in pipes:
        os.close(pr)
        os.close(pw)
    for pid in processes:
        os.waitpid(pid, 0)


def shell():
    while True:
        try:
            ps1 = os.getenv("PS1", "$ ")
            os.write(1, ps1.encode())
            command = sys.stdin.readline().strip()
            if not command:
                continue
            
            if "|" in command:
                execute_pipeline(command.split("|"))
            else:
                tokens, background, input_file, output_file = parse_command(command)
                execute_command(tokens, background, input_file, output_file)
        except EOFError:
            sys.exit(0)
        except KeyboardInterrupt:
            os.write(1, b"\n")

if __name__ == "__main__":
    shell()
