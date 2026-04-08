import usi_process

#コマンドの送信
def send(proc, cmd, option=""):
    proc.stdin.write(cmd + " " + option + "\n")
    proc.stdin.flush()

#コマンドの解析
def usi_isready(proc):
    send(proc, "isready")
    while True:
        line = proc.stdout.readline().strip()
        if line == "readyok":
            return
def usi_go(proc, option=""):
    send(proc, "go", option)
    while True:
        line = proc.stdout.readline().strip()
        if line.startswith("bestmove"):
            bestmove = line.split()[1]
            return bestmove
def usi_position(proc, proc_2, sfen, moves):
    send(proc, "position", f"sfen {sfen} moves {moves}")
    send(proc_2, "position", f"sfen {sfen} moves {moves}")