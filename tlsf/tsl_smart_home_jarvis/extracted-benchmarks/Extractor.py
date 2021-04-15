import subprocess
import sys
import tempfile
import os
import re
import glob

def getFiles(directory):
    files = []
    for r, d, f in os.walk(directory):
        for file in f:
            if file.endswith(".tsl"):
                files.append(os.path.join(r, file))
    return files


def escape_ansi(line): #https://stackoverflow.com/a/38662876
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', line)

def checkFile(filepath):
    ret = subprocess.run(["tslcheck", filepath], cwd=os.getcwd(), universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #print(ret.stdout)
    return escape_ansi(ret.stdout)[:5] == "valid"



def copyFiles(source, target, version, files):
    for f in files:
        filename = os.path.splitext(os.path.basename(f))[0]
        filepath = target + "/" + filename + "_" + version + ".tsl"
        subprocess.run(["tslresolve " + f + " > " + filepath], cwd=source, shell=True)
        if not checkFile(filepath):
            invpath = target + "/invalid/" + filename + "_" + version + ".tsl"
            subprocess.run(["mv " + filepath + " " + invpath], shell=True)
        

def checkoutVersion(tmpdir, version):
    subprocess.run(["git checkout " + version], cwd=tmpdir, shell=True)

def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        print(sys.argv[1])
        subprocess.run(["git clone " + sys.argv[1] + " " + tmpdir], shell=True)
        ret = subprocess.run(["git", "rev-list", "--all"], cwd=tmpdir, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        versions = [x[:8] for x in ret.stdout.strip().split('\n')]
        print(versions)
        #versions = versions[:5]
        try:
            os.mkdir(os.path.join(os.path.abspath(os.getcwd()), "invalid"), 0o755)
        except:
            pass
        for version in versions:
            checkoutVersion(tmpdir, version)
            files = getFiles(tmpdir)
            #print(files)
            copyFiles(tmpdir, os.path.abspath(os.getcwd()), version, files)
        #print(checkFile(getFiles(os.getcwd())[0]))
        filelist = [f for f in glob.glob("*.tsl")]
        md5sums = set()
        for f in filelist:
            ret = subprocess.run(["md5sum", f], cwd=os.getcwd(), universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            md5sum = ret.stdout[:32]
            if md5sum in md5sums:
                ret = subprocess.run(["rm", f], cwd=os.getcwd(), universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            else:
                md5sums.add(md5sum)

if __name__ == '__main__':
    main()
