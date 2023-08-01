from typing import List, Dict
from pathlib import Path
import glob
import os

from timm_scripts import train


def objective_function(configuration: Dict, epoch: int, previous_epoch: int, checkpoint_path: Path) -> List:
    seed = 0
    model = 'mobilevit_xxs'
    dataset = 'torch/cifar10'
    data_dir = './data/cifar10'
    # dataset = 'folder/cats_vs_dogs_mini'
    # data_dir = './data/cats_vs_dogs_mini'
    dataset_download = True

    path_parts = checkpoint_path.parts
    experiment_name = path_parts[-2]
    output_checkpoint_path = Path(*path_parts[:-2])
    resume_checkpoint_path = checkpoint_path if previous_epoch > 0 else ''

    metric = train.main_with_args(
        dataset=dataset,
        data_dir=data_dir,
        model=model,
        epochs=epoch,
        seed=seed,
        dataset_download=dataset_download,
        resume=str(resume_checkpoint_path),
        output=str(output_checkpoint_path),
        experiment=experiment_name,
        checkpoint_hist=1,
        val_split="test",
        eval_metric='top1',
        batch_size=128,
        opt="adam",
        sched="None",
        workers=8,
        amp=True,
        **configuration,
    )

    # remove extra checkpoint files to save space
    trial_checkpoint_path = Path(*path_parts[:-1]) / 'checkpoint*'
    files = glob.glob(str(trial_checkpoint_path))

    for file in files:
        try:
            os.remove(file)
        except OSError as ex:
            print(f"Error: {file} : {ex.strerror}")

    return metric