""" Wraps and evaluate the objective function and manages checkpoints for each trial.
"""

from pathlib import Path
from typing import List, Dict, Callable, Union, Tuple
import time
import shutil

from hpo4dl.utils.configuration_dataclasses import ConfigurationInfo
from hpo4dl.graybox_wrapper.abstract_graybox_wrapper import AbstractGrayBoxWrapper


class GrayBoxWrapper(AbstractGrayBoxWrapper):
    """ Wraps and evaluate the objective function and manages checkpoints for each trial.
    """

    def __init__(
        self,
        checkpoint_path: Path,
        objective_function: Callable[[Dict, int, int, str], Union[List[Dict], Dict]],
    ):
        self.objective_function = objective_function
        self.checkpoint_path = checkpoint_path
        self.previous_fidelities: Dict[int, int] = {}
        self.trial_results: Dict[Tuple[int, int], List[Dict]] = {}
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    def start_trial(
        self,
        configuration_info: List[ConfigurationInfo],
        epoch: List[int]
    ) -> List[Dict]:
        """ Evaluate a batch of configurations.

        Args:
            configuration_info: IDs of the configurations to be evaluated.
            epoch: The epochs to be evaluated.

        Returns:
            List[Dict]: Configuration results for all configuration/epoch pair.
        """
        all_configuration_results = []
        for trial_config_info, trial_epoch in zip(configuration_info, epoch):
            configuration_results = self._run(configuration_info=trial_config_info, epoch=trial_epoch)
            all_configuration_results.extend(configuration_results)

        return all_configuration_results

    def _run(self, configuration_info: ConfigurationInfo, epoch: int) -> List[Dict]:
        """ Evaluate a configuration.

        Args:
            configuration_info: ID of the configuration to be evaluated.
            epoch: The epoch to be evaluated.

        Returns:
            Dict: Configuration results for the given configuration/epoch pair.
        """
        configuration_id = configuration_info.configuration_id
        configuration = configuration_info.configuration

        if (configuration_id, epoch) in self.trial_results:
            return self.trial_results[(configuration_id, epoch)]

        checkpoint_path = self.get_checkpoint_path(configuration_id)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        if configuration_id in self.previous_fidelities:
            previous_epoch = self.previous_fidelities[configuration_id]
        else:
            previous_epoch = 0

        start_time = time.perf_counter()
        configuration_result = self.objective_function(
            configuration, epoch, previous_epoch, str(checkpoint_path)
        )
        end_time = time.perf_counter()
        execution_time = end_time - start_time

        if not isinstance(configuration_result, List):
            configuration_result = [configuration_result]

        self.verify_configuration_results(configuration_result)

        single_epoch_execution_time = execution_time / len(configuration_result)

        configuration_results = []
        for entry in configuration_result:
            configuration_result = {
                **entry,
                'configuration_id': configuration_id,
                'configuration': configuration,
                'time': single_epoch_execution_time,
            }
            configuration_results.append(configuration_result)

        self.previous_fidelities[configuration_id] = epoch
        self.trial_results[(configuration_id, epoch)] = configuration_results

        return configuration_results

    def verify_configuration_results(self, configuration_result: List[Dict]):
        """ Verify that configuration results have epoch and metric entries.

        Args:
            configuration_result: Evaluated configuration results.
        """
        for entry in configuration_result:
            if "epoch" not in entry:
                raise ValueError("epoch entry missing from objective function results.")
            if "metric" not in entry:
                raise ValueError("metric entry missing from objective function results.")

    def get_checkpoint_path(self, configuration_id: int) -> Path:
        """ Gets the checkpoint path for the given configuration.

        Args:
            configuration_id: The ID of the configuration.

        Returns:
            Path: The checkpoint path.
        """
        return self.checkpoint_path / f'trial_{configuration_id}'

    def close(self) -> None:
        """ Closes the wrapper and cleans up the checkpoint directory.
        """
        if self.checkpoint_path.exists():
            shutil.rmtree(self.checkpoint_path)
