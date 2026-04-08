import subprocess

def usi_process(engine_path, engine_path_2):
        # エンジン起動
    proc_black = subprocess.Popen(
        [engine_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    proc_white = subprocess.Popen(
        [engine_path_2],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    return proc_black, proc_white