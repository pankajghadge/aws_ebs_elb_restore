config = {

    # AWS credentials for the IAM user (alternatively can be set up as environment variables)
    'aws_access_key': 'XXXXXXXXXXXXXX',
    'aws_secret_key': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXX',

    # EC2 info about your server's region
    'ec2_region_name': 'eu-west-2',
    'ec2_region_endpoint': 'fcu.eu-west-2.aws.com',

    # Availability zone
    'availability_zone': 'eu-west-2b',

    # Tag of the EBS volume you want to take the snapshots of
    'tag_name': 'Name',
    'tag_value': 'filer01.project.private.ppd.vpc-eu01.itcompanyname.net',

    # EBS volume size
    'ebs_size': '1000',

    # Mount dir
    'mount_dir': '/shared',

    # LVM physical volumes (pv), volume groups (vg), and logical volumes (lv)
    'vg_name': 'project_shared_vg',
    'lv_name': 'shared_lv',

    # Instance ID
    'instance_id': 'i-xxxxxxx',
    # Number of snapshots to list,
    'limit': 7,

}
