#!/usr/bin/env python

from boto.ec2.connection import EC2Connection
from boto.ec2.regioninfo import RegionInfo
from boto.ec2.blockdevicemapping import BlockDeviceMapping, BlockDeviceType
from boto.utils import get_instance_metadata

import datetime
from dateutil import parser

import dateutil
import time
import sys
import os, errno
import logging
from config import config
import subprocess
import time

# curl http://169.254.169.254/latest/meta-data/block-device-mapping/
# curl http://169.254.169.254/latest/meta-data/block-device-mapping/ebs3
# curl http://169.254.169.254/latest/meta-data/block-device-mapping/ebs5
# curl http://169.254.169.254/latest/meta-data/block-device-mapping/ebs6

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def get_ec2_connection():
    print bcolors.OKBLUE + "FUNCTION: get_ec2_connection" + bcolors.ENDC
    aws_access_key      = config['aws_access_key']
    aws_secret_key      = config['aws_secret_key']
    ec2_region_name     = config['ec2_region_name']
    ec2_region_endpoint = config['ec2_region_endpoint']

    region = RegionInfo(name=ec2_region_name, endpoint=ec2_region_endpoint)

    try:
        conn = EC2Connection(aws_access_key, aws_secret_key, region=region)
    except Exception, e:
        print "ERROR: Unable to connect to EC2 API, Please check the credentials OR Connection:", e
        sys.exit()

    return conn

def get_snapshots_details(conn, filters):
    print bcolors.OKBLUE + "FUNCTION: get_snapshots_details" + bcolors.ENDC
    ebs_snapshot_discribe_limit = config['limit']

    snapshots = conn.get_all_snapshots(filters=filters)
    snapshots = sorted(snapshots, key=get_key, reverse=True)
    time_limit = datetime.datetime.now() - datetime.timedelta(days=ebs_snapshot_discribe_limit)
    snapshots_date_details = dict()

    for snapshot in snapshots:
        if parser.parse(snapshot.start_time).date() >= time_limit.date():
           snapshots_date_details.setdefault(parser.parse(snapshot.start_time).date(), []).append(snapshot.id)

    snapshots_date_details = sorted(snapshots_date_details.items(), reverse=True)
    return snapshots_date_details

#This function is not Required, Just kept for future
def get_block_device_mapping(conn, instance_id):
    print bcolors.OKBLUE + "FUNCTION: get_block_device_mapping" + bcolors.ENDC
    return conn.get_instance_attribute(
            instance_id=instance_id,
            attribute='blockDeviceMapping'
            )['blockDeviceMapping']

def get_key(snapshot):
    return snapshot.start_time

# Main menu
def main_menu(snapshots_date_details, host):
    print bcolors.OKBLUE + "FUNCTION: main_menu" + bcolors.ENDC
    #os.system('clear')
    print "########################### MAIN MENU ################################"
    print "Please select the EBS+LVM snapshot for Recovery on "+ host
    for index, value in enumerate(snapshots_date_details):
       print str(index+1)+")", value[0], value[1]
    print "0) Quit"
    print "########################### END OF MENU ##############################"

    choice = raw_input(" >>  ")
    if int(choice) == 0: exit()

    if choice.isdigit() and int(choice) <= len(snapshots_date_details):
        print "\nYou have selected the "+choice+" option ", snapshots_date_details[int(choice)-1]
        print "1) To Continue"
        print "2) To Go Back To Main Menu"
        print "0) Quit"
        ch = raw_input(" >>  ")
        if int(ch) == 0: exit()

        if int(ch) == 1:
           return snapshots_date_details[int(choice)-1]
        elif int(ch) == 2:
           os.system('clear')
           main_menu(snapshots_date_details, host)
        else:
           print bcolors.FAIL + "ERROR: Invalid selection, please try again." + bcolors.ENDC
           main_menu(snapshots_date_details, host)
    return False

def attach_snapshot(conn, snapshots_attach_details):
    print bcolors.OKBLUE + "FUNCTION: attach_snapshot" + bcolors.ENDC

    instance_id = config['instance_id']
    tuple_devices  = ('/dev/sdb','/dev/sdc','/dev/sdd','/dev/sde','/dev/sdf','/dev/sdg','/dev/sdh', \
                     '/dev/sdi','/dev/sdj','/dev/sdk','/dev/sdl','/dev/sdm','/dev/sdn','/dev/sdo', \
                     '/dev/sdp','/dev/sdq','/dev/sdr','/dev/sds','/dev/sdt','/dev/sdu','/dev/sdv', \
                     '/dev/sdw','/dev/sdx','/dev/sdy','/dev/sdz')

    device_counter = 0
    ebs_size       = config['ebs_size']
    zone           = config['availability_zone']
    volume_ids     = []

    for snapshot in snapshots_attach_details[1]:
        print snapshot
        try:
            vol = conn.create_volume(ebs_size, zone, snapshot, volume_type="io1", iops=3000, dry_run=False)
            vol.add_tag(config['tag_name'], 'admin.cls.private.ppd.vpc-eu02.it3ds.net')
            #vol.add_tag(config['tag_name'], config['tag_value'])
            volume_ids.append(vol.id)
            time.sleep(5)
        except:
            print bcolors.FAIL + "ERROR: Can't create a volume" + bcolors.ENDC
            print bcolors.FAIL + "ERROR: Check your current volume size quota with your cloud provider" + bcolors.ENDC
            if len(volume_ids) > 0:
               print bcolors.FAIL + "ERROR: Please delete these volumes manually from Cloud Management Console: " + bcolors.ENDC, volume_ids
               exit()

    time.sleep(10)

    counter = 0
    for id in volume_ids:
        attached_volume_flag = False
        while ((len(tuple_devices) > device_counter) and (attached_volume_flag == False)):
            try:
                print "PROCESSING: Attaching volume", id, "to device ", tuple_devices[device_counter]
                result = conn.attach_volume(id, instance_id, tuple_devices[device_counter],dry_run=False)
                attached_volume_flag = True
                counter += 1
                time.sleep(5)
            except:
                print "NOTE: Can't attach the volume ", id, " to device ", tuple_devices[device_counter]
                print "NOTE: Trying next device"
                time.sleep(5)

            device_counter += 1

    time.sleep(10)
    if counter != len(volume_ids):
       print bcolors.FAIL + "ERROR: Can't attach all EBS volume" + bcolors.ENDC
       print bcolors.FAIL + "ERROR: Please delete/detach these volumes manually from Cloud Management Console: "+ bcolors.ENDC, volume_ids
       exit()

    return volume_ids

def check_vg_name_exists(vg_name=config['vg_name']):
    print bcolors.OKBLUE + "FUNCTION: check_vg_name_exists:" + bcolors.ENDC
    command = 'vgdisplay --short | awk \'{gsub(/"/, "", $1); print $1}\''
    vg_names = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, err = vg_names.communicate()
    output = output.splitlines()
    if vg_name in output:
       return True
    return False

def get_pv_name_attached_to_vg(vg_name=config['vg_name']):
    print bcolors.OKBLUE + "FUNCTION: get_pv_name_attached_to_vg:" + bcolors.ENDC
    command = 'pvdisplay --columns |  awk \'FNR > 1 {print $1, $2}\''
    pv_names = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    lvm_details = dict()
    while True:
        line = pv_names.stdout.readline()
        if line != '':
           row = line.split()
           lvm_details.setdefault(row[1], []).append(row[0])
        else:
           break

    return lvm_details[vg_name]

"""
def restore_lvm_volume(conn, ebs_volume_ids):
    print "In restore_lvm_volume(conn, ebs_volume_ids):"
    block_device_mapping = get_block_device_mapping(conn, instance_id)
    for device in block_device_mapping:
        print('Device: {}'.format(device))
        bdt = block_device_mapping[device]
        print('\tVolumeID: {}'.format(bdt.volume_id))
"""

def umount_lvm():
    print bcolors.OKBLUE + "FUNCTION: umount_lvm" + bcolors.ENDC
    command = 'umount -f '+config['mount_dir']
    print "EXECUTING: "+command
    umount = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, err = umount.communicate()
    if err :
       print bcolors.FAIL + "ERROR: Unable to umount", config['mount_dir'] + bcolors.ENDC
       return False

    directory_counter = 1
    directory_name = config['mount_dir']+"_"+str(directory_counter)
    flag = True
    while(flag):
       if os.path.exists(directory_name):
          directory_counter +=1
          directory_name = config['mount_dir']+"_"+str(directory_counter)
       else:
          flag = False

    try:
        os.makedirs(directory_name)
    except OSError as e:
        if e.errno != errno.EEXIST:
           return False

    ##Deactivate the LVM Group
    command = 'vgchange -a n '+config['vg_name']
    print "EXECUTING: "+command
    deactivate_vg = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, err = deactivate_vg.communicate()


    pv_names = get_pv_name_attached_to_vg(config['vg_name'])
    ## Change the UUID of existing PV Name
    for pv_name in pv_names:
        command = 'pvchange -u '+pv_name
        print "EXECUTING: "+command
        pvchange = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, err = pvchange.communicate()


    ## Change the UUID of existing VG Name, we will use vgimportclone
    command = 'vgimportclone -n '+config['vg_name']+'_'+str(directory_counter)+' '+' '.join(pv_names)
    print "EXECUTING: "+command
    vgimportclone = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, err = vgimportclone.communicate()

    ## Activate the LVM Group
    command = 'vgchange -ay '+config['vg_name']+'_'+str(directory_counter)
    print "EXECUTING: "+command
    activate_vg = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, err = activate_vg.communicate()

    #Rename the existing VG Group
    """
    command = 'vgrename '+config['vg_name']+' '+config['vg_name']+'_'+str(directory_counter)
    print "EXECUTING: "+command
    vgrename = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, err = vgrename.communicate()
    """

    #Mount old LVM to other directory
    command = 'mount /dev/'+config['vg_name']+'_'+str(directory_counter)+'/'+config['lv_name']+' '+directory_name
    print "EXECUTING: "+command
    mount = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, err = mount.communicate()
    if err :
       print bcolors.FAIL + "ERROR: Unable to mount old lvm" + bcolors.ENDC
       return False

    return True

def mount_lvm():
    print bcolors.OKBLUE + "FUNCTION: mount_lvm:" + bcolors.ENDC
    try:
        os.makedirs(config['mount_dir'])
    except OSError as e:
        if e.errno != errno.EEXIST:
           raise

    command = 'mount /dev/'+config['vg_name']+'/'+config['lv_name']+' '+config['mount_dir']
    print "EXECUTING: "+command
    mount = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, err = mount.communicate()
    if err :
       print bcolors.FAIL + "ERROR: Unable to mount lvm" + bcolors.ENDC
       print err
       return False
    return True

# Exit program
def exit():
    sys.exit()

# Main Program
if __name__ == "__main__":
    print bcolors.OKBLUE + "FUNCTION: __main__" + bcolors.ENDC
    instance_id   = config['instance_id']
    conn          = get_ec2_connection()

    filters       = { 'tag:' + config['tag_name']: config['tag_value'] }
    snapshots     = get_snapshots_details(conn, filters)
    snapshot_data = main_menu(snapshots, config['tag_value'])

    if check_vg_name_exists():
       if umount_lvm():
          print bcolors.OKGREEN + "SUCESS: Renamed/Moved the existing volume" + bcolors.ENDC
       else:
          print bcolors.FAIL + "ERROR: Existing volume can't be Renamed/Moved" + bcolors.ENDC
          print bcolors.FAIL + "ERROR: We Are Quitting" + bcolors.ENDC
          exit()

    if snapshot_data is not False:
       volume_ids = attach_snapshot(conn, snapshot_data)

    if mount_lvm():
       print bcolors.OKGREEN + "SUCESS: Recovered the new volume "+config['mount_dir'] + bcolors.ENDC
    else:
       print bcolors.FAIL + "ERROR: Unable to recover the new volume "+config['mount_dir'] + bcolors.ENDC
