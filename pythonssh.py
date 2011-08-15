import paramiko
import sys
hostname = sys.argv[1]
user = sys.argv[2]
passwd = sys.argv[3]
command = sys.argv[4]

ssh = paramiko.SSHClient()
# add key from unknown host without prompt
ssh.set_missing_host_key_policy(
    paramiko.AutoAddPolicy())
try:
    ssh.connect(hostname, username=user, 
    password=passwd)
except paramiko.SSHException:
    print "Error in establishing SSH session"
    sys.exit(2)
except paramiko.BadHostKeyException:
    print "Server key could not be verified"
    sys.exit(2)
except paramiko.AuthenticationException:
    print "Authentication Falied"
    sys.exit(2)
except paramiko.socket.error:
    print "Socket Error while connecting"
    sys.exit(2)


#stdin, stdout, stderr = ssh.exec_command(
#    "sudo ls -l")
#stdin.write('password\n')
#stdin.flush()
try:
    #stdin, stdout, stderr = ssh.exec_command("python worker.py")
    stdin, stdout, stderr = ssh.exec_command(command)
    print stdout.readlines()
except paramiko.SSHException:
    print "Server fails to execute the command"
    
#data = stdout.read.splitlines()
#for line in data:
#    print line
ssh.close()
