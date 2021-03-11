"""
Create SageMaker training job for standard libs
    + Support both modes:
        "local" for debuging using local machine
        "online" for actual creating a training job on SageMaker instance
    + Default S3 output: s3://rnd-ocr/zcinnamon/CURE/output/<full_job_name>
    + Default S3 checkpoints: s3://rnd-ocr/zcinnamon/CURE/checkpoints_<sm_base_job_name>_<YearMonthDay>
    + Default instance: ml.p3.2xlarge (1 x V100)
    + Default using Spot training instance
    + Using kwargs to feed forward command-line arguments from this file to git_entry_point arguments
    Example:
        $python scripts/run_sagemaker.py --mode local --sm_base_job_name zcinnamon-cure-cnn --kwargs "--config scripts/configs/default_config.yaml
         --save_dir /opt/ml/checkpoints --bs 256 --n_epochs 100"
        --config, --bs, --n_epochs to git_entry_point's arguments
"""
import sagemaker
import time
import os
import boto3
import argparse

from typing import List, Dict

# parse arguments
parser = argparse.ArgumentParser(description="Cinnamon AI Labs - R&D department - CURE framework\n "
                                             "Create training job on SageMaker environment",
                                 formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('--mode', metavar='mode', nargs='?', const="local", default="local", choices=['local', 'online'],
                    help='Choose mode: local debug or SageMaker online training')
parser.add_argument('--ecr_repo', metavar='ecr_repo', nargs='?', default="sagemaker-lib-layout",
                    help='Set ECR repo name')
parser.add_argument('--ecr_image_tag', metavar='ecr_image_tag', nargs='?', default="lib-layout-master",
                    help='Set Docker Image tag')
parser.add_argument('--sm_base_job_name', metavar='sm_base_job_name', nargs='?', default="train-lib-layout",
                    help='Set prefix name for this training job')
parser.add_argument('--sm_instance_type', metavar='sm_instance_type', nargs='?', default='ml.g4dn.xlarge',
                    help='Choose training instance type')
parser.add_argument('--sm_disk_volume', metavar='sm_disk_volume', nargs='?', type=int, default=100,
                    help='Training instance disk\'s volume (in GB)')
parser.add_argument('--git_repo', metavar='git_repo', nargs='?', default="lib-layout",
                    help='Github repo name which you want to train')
parser.add_argument('--git_branch', metavar='git_branch', nargs='?', default="",
                    help='A branch which you want to work on, if blank then use `master` branch')
parser.add_argument('--git_entry_point', metavar='git_entry_point', nargs='?', default="scripts/train.py",
                    help='Entry point from Github repo to start training.')
parser.add_argument('--git_commit_or_tag', metavar='git_commit_or_tag', nargs='?', type=str, default='None',
                    help='A version which you want to work on, could be commit id or tag, '
                         'if blank for latest commit on branch')
parser.add_argument('--git_secret', metavar='git_secret', nargs='?', type=str,
                    default="arn:aws:secretsmanager:us-west-2:787422137509:secret:CinnamonBuilder_github_ssh",
                    help='Secret name in AWS secret manager to get git access token')
parser.add_argument('--data_root_dir', metavar='data_root_dir', nargs='?', type=str, default='./data',
                    help='Local data root directory to shorten data path args'
                         'the script will create soft link between /opt/ml/input/data into this location')
parser.add_argument('--env_update', metavar='env_update', nargs='?', default="True",
                    help='Update environment of Docker Image to latest setup.py, '
                         'if False then use the pre-installed environment of Docker Image')
parser.add_argument('--env_extras_require', metavar='env_extras_require', nargs='?', default="None",
                    help='Extra requirement for installing dependencies')
parser.add_argument('--s3_input_channel', metavar='s3_input_channel', nargs='+', type=str,
                    default='s3://rnd-ocr/DATASET/ForInvoice/Invoice_from_victor',
                    help='S3 URIs to a folder or file (type:<string>/<list of string>)')
parser.add_argument('--s3_output_channel', metavar='s3_output_channel', nargs='?', type=str,
                    default='s3://rnd-ocr/zcinnamon/CURE/output/',
                    help='S3 URIs for saving model (type:<string>)')
parser.add_argument('--aws_role', metavar='aws_role', nargs='?', type=str,
                    default="arn:aws:iam::533155507761:role/service-role/AmazonSageMaker-ExecutionRole-20190312T160681",
                    help='AWS IAM role for creating training job')
parser.add_argument('--aws_region', metavar='aws_region', nargs='?', type=str,
                    default="us-west-2",
                    help='AWS region. Default Cinnamon AIRs are only able to create SM training job on us-west-2 region.')
parser.add_argument('--aws_central_account', metavar='aws_central_account', nargs='?', type=str,
                    default="533155507761",
                    help='ID of AWS central account which store data, ECR repos, ...')
parser.add_argument('--kwargs', metavar='kwargs', nargs='?', type=str,
                    help='Arguments for entry_point (string). '
                         'This would be parsed into another arguments for feeding into entry_point.\n'
                         'Example:\n'
                         '$python scripts/run_sagemaker.py --mode local --sm_base_job_name train-lib-ocr --kwargs \"--config scripts/configs/default_config.yaml'
                         '--save_dir /opt/ml/checkpoints --n_epochs 100\"\n'
                         'config, save_dir, n_epochs is argument which you want to parse git_entry_point\'s arguments')


def get_channel_name(url):
    """
    Get S3 channel name from S3 URI
    Examples
    --------
    >>> # Case 1: prefix is a folder
    >>> url = "s3://rnd-ocr/DATASET/Showadenko"
    >>> get_channel_name(url)
    "Showadenko"
    >>> # Case 2: prefix is a file
    >>> url = "s3://rnd-ocr/DATASET/SCUT-EPT_Mini1k/SCUT-EPT_test_alphabet.txt"
    >>> get_channel_name(url)
    "SCUT-EPT_test_alphabet"
    Parameters
    ----------
    url : str
        S3 URI link
    """
    if '.' in os.path.basename(url):
        # File
        return os.path.splitext(os.path.basename(url))[0]
    else:
        # Folder
        return os.path.basename(url)


def createInputChannel(channelPrefixes, InputMode="File", S3DataType="S3Prefix", S3DataDistributionType="FullyReplicated"):
    """Create input channel for Estimator
    This function support create multiple channels for a training session
    Example:
    ----------
    channelPrefixes = ["s3://rnd-ocr/DATASET/Okaya", "s3://rnd-ocr/DATASET/SCSK", "s3://rnd-ocr/DATASET/Showadenko"]
    If InputMode="File", SageMaker will download from S3 to training instance's local storage when initializing instance:
        s3://rnd-ocr/DATASET/Okaya      => /opt/ml/input/data/Okaya
        s3://rnd-ocr/DATASET/SCSK       => /opt/ml/input/data/SCSK
        s3://rnd-ocr/DATASET/Showadenko => /opt/ml/input/data/Showadenko
    Your training code must be modified to expect input data from those "/opt/ml/input/data" folders
    Parameters
    ----------
    channelPrefixes : list of S3 prefixes
    """
    InputDataList = []

    for x in channelPrefixes:
        InputDataList.append({
            "ChannelName": get_channel_name(x),
            "DataSource": {
                "S3DataSource": {
                    "S3DataType": S3DataType,
                    "S3Uri": x,
                    "S3DataDistributionType": S3DataDistributionType
                }
            },
            "CompressionType": "None",
            "RecordWrapperType": "None",
            "InputMode": InputMode,
        })

    return InputDataList


def parse_hyperparameters_from_args(args: argparse.Namespace) -> Dict:
    """
    Get hyperparameters from argumentparse
    Parameters
    ----------
    args: argparse.Namespace, output of parser.parse_args()
    Returns
    -------
    dict: to use in Estimator hyperparameters
    """

    hypers_dict = {}
    if args.kwargs:
        l_kwargs = args.kwargs.strip().split()
        hypers_dict = {l_kwargs[x]: l_kwargs[x + 1] for x in range(0, len(l_kwargs), 2)}

    hypers_dict["git_entry_point"] = args.git_entry_point

    # Add info for training std libs
    hypers_dict.update({
        "git_repo": args.git_repo,
        "git_branch": args.git_branch,
        "git_commit_or_tag": args.git_commit_or_tag,
        "git_entry_point": args.git_entry_point,
        "git_secret": args.git_secret,
        "env_update": args.env_update,
        "env_extras_require": args.env_extras_require,
        "data_root_dir": args.data_root_dir,
    })

    # Cast types of value to string in hyperparameters
    for k, v in hypers_dict.items():
        if not isinstance(v, str):
            try:
                hypers_dict[k] = str(v)
            except:
                hypers_dict[k] = 'None'

    print(f"[INFO] Input hyperparameters: {hypers_dict}")
    return hypers_dict


if __name__ == "__main__":

    args = parser.parse_args()

    # Default Cinnamon's info for SageMaker
    aws_role = args.aws_role
    aws_region = args.aws_region
    aws_central_account = args.aws_central_account

    # ECR repository
    ecr_repo = args.ecr_repo
    # ECR image tag
    ecr_image_tag = args.ecr_image_tag
    # SageMaker training instance configuration (for "online" mode)
    sm_base_job_name = args.sm_base_job_name
    sm_instance_type = args.sm_instance_type
    sm_disk_volume = args.sm_disk_volume

    # S3 input channel uri
    s3_input_channel = args.s3_input_channel if isinstance(args.s3_input_channel, List) else [args.s3_input_channel]

    # Set VNT
    if hasattr(time, 'tzset'):
        os.environ['TZ'] = 'Asia/Ho_Chi_Minh'
        time.tzset()

    s3_model_output = args.s3_output_channel
    s3_checkpoints_output = os.path.join(s3_model_output,
                                       f"checkpoints_{sm_base_job_name}_{time.strftime('%Y%m%d', time.localtime())}")

    image_uri = '{}.dkr.ecr.{}.amazonaws.com/{}:{}'.format(aws_central_account, aws_region, ecr_repo, ecr_image_tag)

    # Maximum training days
    day_run = 5
    train_max_run = day_run * 24 * 3600

    hypers = parse_hyperparameters_from_args(args)

    # ########################## RUN THE ESTIMATOR #################
    if 'local' in args.mode:
        # [local] use local machine for debugging
        print("[local] Start training job on local machine...")

        # replace instance type to 'local' (cpu) or 'local_gpu' (gpu)
        sm_instance_type = 'local_gpu'

        estimator = sagemaker.estimator.Estimator(
            image_uri=image_uri,
            base_job_name=sm_base_job_name,
            role=aws_role,
            instance_count=1,
            input_mode='File',
            instance_type=sm_instance_type,
            output_path=s3_model_output,
            max_run=train_max_run,
            sagemaker_session=sagemaker.LocalSession(),
            hyperparameters=hypers)

        if isinstance(s3_input_channel, list):
            input_dict = {}
            for x in s3_input_channel:
                input_dict[get_channel_name(x)] = x
        else:
            input_dict = {get_channel_name(s3_input_channel): s3_input_channel}
        estimator.fit(inputs=input_dict)
    else:
        # [online] Create online SageMaker training job
        print("[online] Start training job on SM instance ...")

        pipe_job = sm_base_job_name + '-' + time.strftime("VNT%Y%m%d-%H%M%S", time.localtime())
        InputMode = "File"

        print(f"[INFO] Training job full name: {pipe_job}")
        base_job_uri = "https://us-west-2.console.aws.amazon.com/sagemaker/home?region=us-west-2#/jobs/"
        print(f"[INFO] Training job link:\n {base_job_uri + pipe_job}")

        # Create Input data channel
        InputDataList = createInputChannel(s3_input_channel)

        # Get current AWS account for tags
        iam = boto3.client('iam')
        iam_arn = iam.get_user()['User']['Arn']

        training_params = {
            "RoleArn": aws_role,
            "TrainingJobName": pipe_job,
            "AlgorithmSpecification": {
                # "MetricDefinitions": [
                #     {'Name': 'train:loss_T', 'Regex': '.*Loss_T: ([0-9\\.]+) Loss_D: [0-9\\.]+.*'},
                #     {'Name': 'train:loss_D', 'Regex': '.*Loss_T: [0-9\\.]+ Loss_D: ([0-9\\.]+).*'},
                # ],
                "TrainingImage": image_uri,
                "TrainingInputMode": InputMode,
            },
            "ResourceConfig": {
                "InstanceCount": 1,
                "InstanceType": sm_instance_type,
                "VolumeSizeInGB": 100
            },
            "InputDataConfig": InputDataList,
            "OutputDataConfig": {
                "S3OutputPath": s3_model_output,
            },
            "StoppingCondition": {
                "MaxRuntimeInSeconds": train_max_run,
                "MaxWaitTimeInSeconds": train_max_run*2,
            },
            "HyperParameters": hypers,
            "CheckpointConfig": {
                "S3Uri": s3_checkpoints_output,
                "LocalPath": "/opt/ml/checkpoints/",
            },
            "EnableManagedSpotTraining": True,
            "Tags": [
                {
                    "Key": "type",
                    "Value": "std-lib training"
                },
                {
                    "Key": "iam_arn",
                    "Value": iam_arn
                }
            ],
        }

        sm_session = sagemaker.Session()
        sm = boto3.client('sagemaker')
        sm.create_training_job(**training_params)

        status = sm.describe_training_job(TrainingJobName=pipe_job)['TrainingJobStatus']
        print(f"[INFO] Training Job Status: {status}")
        sm_session.logs_for_job(job_name=pipe_job, wait=True)
        sm.get_waiter('training_job_completed_or_stopped').wait(TrainingJobName=pipe_job)
        status = sm.describe_training_job(TrainingJobName=pipe_job)['TrainingJobStatus']
        print("[INFO] Training job ended with status: " + status)
        if status == 'Failed':
            message = sm.describe_training_job(TrainingJobName=pipe_job)['FailureReason']
            print('Training failed with the following error: {}'.format(message))
            raise Exception('Training job failed')