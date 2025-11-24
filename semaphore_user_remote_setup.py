#!/usr/bin/env python3
"""
SSH Remote User Setup Script
This script automates the process of setting up a semaphore user on a remote host
with passwordless sudo access and SSH key authentication.
"""

import argparse
import sys
import os
import paramiko
from scp import SCPClient
import subprocess

def execute_ssh_command(ssh_client, command, sudo_password=None, dry_run=False):
    """Execute a command over SSH and return the result."""
    if dry_run:
        print(f"[DRY RUN] Would execute: {command}")
        return True, "dry-run-simulated-output"
    
    try:
        if sudo_password and command.startswith('sudo '):
            # For sudo commands, we need to handle password input
            command = f"echo '{sudo_password}' | sudo -S {command[5:]}"
        
        stdin, stdout, stderr = ssh_client.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        if exit_status != 0:
            print(f"Command failed: {command}")
            print(f"Error: {error}")
            return False, error
        return True, output
    except Exception as e:
        print(f"Error executing command: {e}")
        return False, str(e)

def scp_put_file(scp_client, local_file, remote_file, dry_run=False):
    """Transfer a file via SCP."""
    if dry_run:
        print(f"[DRY RUN] Would transfer file: {local_file} -> {remote_file}")
        return True
    
    try:
        scp_client.put(local_file, remote_file)
        return True
    except Exception as e:
        print(f"Error transferring file via SCP: {e}")
        return False

def run_local_command(command, dry_run=False):
    """Execute a local command."""
    if dry_run:
        print(f"[DRY RUN] Would execute locally: {command}")
        return True
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return True
        else:
            print(f"Local command failed: {command}")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error executing local command: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Setup semaphore user on remote host')
    parser.add_argument('target_ip', help='Target IP address to connect to')
    parser.add_argument('--ssh-user', default='root', help='SSH username (default: root)')
    parser.add_argument('--ssh-password', help='SSH password (will prompt if not provided)')
    parser.add_argument('--ssh-key', help='Path to SSH private key')
    parser.add_argument('--ssh-port', type=int, default=22, help='SSH port (default: 22)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making any changes')
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("=== DRY RUN MODE ===")
        print("No changes will be made to the remote system or local system.")
        print("=" * 50)
    
    # Get SSH password if not provided
    ssh_password = args.ssh_password
    if not ssh_password and not args.ssh_key and not args.dry_run:
        import getpass
        ssh_password = getpass.getpass(f"Enter SSH password for {args.ssh_user}@{args.target_ip}: ")
    
    # SSH client setup
    ssh_client = None
    
    try:
        if not args.dry_run:
            print(f"Connecting to {args.target_ip}...")
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to remote host
            if args.ssh_key:
                ssh_client.connect(
                    hostname=args.target_ip,
                    username=args.ssh_user,
                    key_filename=args.ssh_key,
                    port=args.ssh_port
                )
            else:
                ssh_client.connect(
                    hostname=args.target_ip,
                    username=args.ssh_user,
                    password=ssh_password,
                    port=args.ssh_port
                )
            print("Connected successfully!")
        else:
            print(f"[DRY RUN] Would connect to {args.target_ip} as {args.ssh_user}")
            if args.ssh_key:
                print(f"[DRY RUN] Using SSH key: {args.ssh_key}")
            else:
                print("[DRY RUN] Using password authentication")
        
        # Step 2: Create semaphore user
        print("\n1. Creating semaphore user...")
        success, output = execute_ssh_command(ssh_client, "sudo adduser --disabled-password --gecos '' semaphore", 
                                            ssh_password, args.dry_run)
        if not success and not args.dry_run:
            print("Failed to create semaphore user")
            sys.exit(1)
        print("✓ Semaphore user created successfully")
        
        # Step 3 & 4: Create sudoers file
        print("\n2. Creating sudoers file...")
        sudoers_content = "semaphore ALL=(ALL) NOPASSWD: ALL\n"
        
        if args.dry_run:
            print(f"[DRY RUN] Would create file /etc/sudoers.d/semaphore with content:")
            print(f"[DRY RUN] '{sudoers_content.strip()}'")
        else:
            # Create temporary file
            temp_file = "/tmp/semaphore_sudoers"
            with open(temp_file, 'w') as f:
                f.write(sudoers_content)
            
            # Use SCP to transfer the file
            try:
                scp = SCPClient(ssh_client.get_transport())
                transfer_success = scp_put_file(scp, temp_file, '/tmp/semaphore_sudoers', args.dry_run)
                scp.close()
                
                if transfer_success:
                    # Move file to correct location
                    success, output = execute_ssh_command(
                        ssh_client, 
                        "sudo mv /tmp/semaphore_sudoers /etc/sudoers.d/semaphore",
                        ssh_password,
                        args.dry_run
                    )
                    if not success:
                        print("Failed to move sudoers file")
                        sys.exit(1)
                else:
                    # Alternative method using echo
                    success, output = execute_ssh_command(
                        ssh_client, 
                        f"echo 'semaphore ALL=(ALL) NOPASSWD: ALL' | sudo tee /etc/sudoers.d/semaphore",
                        ssh_password,
                        args.dry_run
                    )
                    if not success:
                        print("Failed to create sudoers file")
                        sys.exit(1)
            except Exception as e:
                print(f"Error during file transfer: {e}")
                sys.exit(1)
            
            # Clean up local temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        print("✓ Sudoers file created successfully")
        
        # Step 5: Set correct permissions
        print("\n3. Setting file permissions...")
        success, output = execute_ssh_command(ssh_client, "sudo chmod 440 /etc/sudoers.d/semaphore", 
                                            ssh_password, args.dry_run)
        if not success and not args.dry_run:
            print("Failed to set permissions")
            sys.exit(1)
        print("✓ Permissions set successfully")
        
        # Step 6: Close SSH connection
        if ssh_client and not args.dry_run:
            ssh_client.close()
            print("\n4. SSH connection closed")
        elif args.dry_run:
            print("[DRY RUN] Would close SSH connection")
        
        # Step 7: Copy SSH key to semaphore user
        print("\n5. Copying SSH key to semaphore user...")
        ssh_key_path = "/home/semaphore/.ssh/id_ed25519.pub"
        
        if args.dry_run:
            print(f"[DRY RUN] Would check for SSH key at: {ssh_key_path}")
            print(f"[DRY RUN] Would execute: sudo ssh-copy-id -i {ssh_key_path} semaphore@{args.target_ip}")
        else:
            if not os.path.exists(ssh_key_path):
                print(f"Warning: SSH key not found at {ssh_key_path}")
                print("Please generate SSH key first with: ssh-keygen -t ed25519 -f /home/semaphore/.ssh/id_ed25519")
            else:
                try:
                    result = subprocess.run([
                        'sudo', 'ssh-copy-id', '-i', ssh_key_path, 
                        f'semaphore@{args.target_ip}'
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        print("✓ SSH key copied successfully!")
                    else:
                        print(f"Failed to copy SSH key: {result.stderr}")
                        # Alternative manual method
                        print("You may need to manually copy the SSH key or check password authentication")
                except Exception as e:
                    print(f"Error during ssh-copy-id: {e}")
        
        print("\n" + "=" * 50)
        if args.dry_run:
            print("DRY RUN COMPLETED SUCCESSFULLY!")
            print("No changes were made to the system.")
        else:
            print("SETUP COMPLETED SUCCESSFULLY!")
            print(f"You can now SSH to the remote host as semaphore user:")
            print(f"  ssh semaphore@{args.target_ip}")
        
    except paramiko.AuthenticationException:
        print("Authentication failed. Please check your credentials.")
        sys.exit(1)
    except paramiko.SSHException as e:
        print(f"SSH connection failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Ensure SSH connection is closed
        if ssh_client and not args.dry_run:
            ssh_client.close()

if __name__ == "__main__":
    main()