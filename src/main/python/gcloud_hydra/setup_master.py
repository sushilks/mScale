import os
import argparse
from shell_command import shell_call

DEFAULT_LOCAL_WORK_DIR = os.environ['HOME'] + "/.setup_master"


def setup(config_file, local_work_dir, dst_work_dir, dst_user_name, setup_ips_dir):
    mesos_marathon_setup_cmd = "python mesos_marathon_setup.py --config_file " + config_file + " --local_work_dir " + \
                               local_work_dir + " --dst_work_dir " + dst_work_dir + " --dst_user_name " + dst_user_name
    shell_call(mesos_marathon_setup_cmd)

    hydra_setup_cmd = "python hydra_setup_script.py --setup_ips_dir " + setup_ips_dir + \
                      " --dst_work_dir " + dst_work_dir + " --dst_user_name " + dst_user_name
    shell_call(hydra_setup_cmd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Script to setup Mesos/Marathon cluster on Google Compute '
                                                 'Engine instances. It will also install Hydra on one of master nodes.')
    parser.add_argument('--config_file', '-f', type=str, default=os.getcwd() + "/setup_config.ini",
                        help='Absolute path of configuration file which dictates the number of master/slave nodes '
                             'along with their machine type. Default is ' + os.getcwd() + '/setup_config.ini .')
    parser.add_argument('--local_work_dir', '-l', type=str, default=DEFAULT_LOCAL_WORK_DIR,
                        help='Script will copy all downloaded/output files in this directory. '
                             'Default is ' + DEFAULT_LOCAL_WORK_DIR)
    parser.add_argument('--dst_work_dir', '-w', type=str, default="/home/plumgrid",
                        help='Destination compute instances work directory. All contents will be uploaded here.')
    parser.add_argument('--dst_user_name', '-u', type=str, default="plumgrid",
                        help='User name on destination compute instance.')
    parser.add_argument('--setup_ips_dir', '-i', type=str, default=os.environ['HOME'],
                        help='Directory where .mesos_masters_ips, .mesos_slaves_ips and '
                             '.mesos_all_ips files are located. Default is /home/$USER/')

    parser.add_argument('--clean', '-c', action='store_true', help='cleanup instances')
    args = parser.parse_args()

    if not os.path.isdir(args.local_work_dir):
        os.makedirs(args.local_work_dir)

    setup(args.config_file, args.local_work_dir, args.dst_work_dir, args.dst_user_name, args.setup_ips_dir)
