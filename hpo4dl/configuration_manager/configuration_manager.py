""" Manages configurations for the hyperparameter tuning process.
"""

from typing import List, Dict, Optional, Set, Tuple
import ConfigSpace as CS
from ConfigSpace import CategoricalHyperparameter
import pandas as pd

from .abstract_configuration_manager import AbstractConfigurationManager


class ConfigurationManager(AbstractConfigurationManager):
    """ Manages configurations for the hyperparameter tuning process.
    """

    def __init__(
        self,
        configuration_space: CS.ConfigurationSpace,
        num_configurations: int = 0,
        seed: Optional[int] = None
    ):
        assert num_configurations >= 0, "num_configurations cannot be negative."
        self.configuration_space = configuration_space
        self.seed = seed
        self.num_configurations = num_configurations
        self.configurations: List[Dict] = []
        self.configurations_set: Set[Tuple] = set()
        self.configurations_df: pd.DataFrame = pd.DataFrame()
        self.log_indicator: List = []
        self.categorical_indicator: List = []
        self.categories: List = []
        self.all_unique_configurations_added = False

        self.configuration_names = self.get_configuration_names()

        if self.seed is not None:
            self.configuration_space.seed(self.seed)

        self.generate_log_indicator()
        self.generate_categorical_indicator()
        self.add_configurations(num_configurations=self.num_configurations)

    def get_configuration_names(self) -> List:
        """ Retrieves configuration names in a specific order.
        The ordering is optimized to minimize column reordering during
        preprocessing when using DyHPO. (log columns, other columns, categorical columns)

        Returns:
            List: A list of configuration names.
        """
        log_names = []
        categorical_names = []
        rem_names = []
        for hparam in list(self.configuration_space.values()):
            if isinstance(hparam, CategoricalHyperparameter):
                categorical_names.append(hparam.name)
            elif hasattr(hparam, 'log') and hparam.log:
                log_names.append(hparam.name)
            else:
                rem_names.append(hparam.name)

        names = log_names + rem_names + categorical_names
        return names

    def get_configurations(self) -> pd.DataFrame:
        """ Returns all generated configurations as a DataFrame.
        Would contain nan values for conditional configuration spaces.

        Returns:
            pd.DataFrame: All generated hyperparameter configurations.
        """
        return self.configurations_df

    def get_configuration(self, configuration_id: int) -> Dict:
        """ Returns the configuration corresponding to the given ID.
        """
        return self.configurations[configuration_id]

    def generate_configurations(self, num_configurations: int) -> List[Dict]:
        """ Generates a specified number of configurations.
        """
        configs = self.configuration_space.sample_configuration(num_configurations)
        hp_configs = [dict(config) for config in configs]
        return hp_configs

    def add_configurations(self, num_configurations: int, max_try_limit: int = 100):
        """ Adds a specified number of configurations to the list.
        Would try to add unique configurations. If failed max_try_limit times, would allow duplicate configurations.

        Args:
            num_configurations: number of configurations to add.
            max_try_limit: maximum number of tries to get non-duplicate configurations.

        Returns:
            int: Number of configurations added.
        """
        num_added = 0
        num_tries = 0
        while num_added < num_configurations and num_tries < max_try_limit:
            num_configurations_to_fill = num_configurations - num_added
            configurations = self.generate_configurations(num_configurations=num_configurations_to_fill)
            # When num_configurations_to_fill=1 output is not a list.
            if not isinstance(configurations, List):
                configurations = [configurations]
            for config in configurations:
                config_tuple = tuple(sorted(config.items()))
                if config_tuple not in self.configurations_set or self.all_unique_configurations_added:
                    self.configurations.append(config)
                    self.configurations_set.add(config_tuple)
                    num_added += 1
            num_tries += 1
        self.configurations_df = pd.DataFrame(self.configurations)
        self.configurations_df = self.configurations_df[self.configuration_names]

        if num_tries == max_try_limit:
            self.all_unique_configurations_added = True
            self.add_configurations(num_configurations - num_added)

    def set_configuration(self, configuration: Dict):
        """ Allows adding specific configuration.
        """
        config_tuple = tuple(sorted(configuration.items()))
        self.configurations.append(configuration)
        self.configurations_set.add(config_tuple)
        self.configurations_df = pd.DataFrame(self.configurations)
        self.configurations_df = self.configurations_df[self.configuration_names]

    def generate_log_indicator(self):
        """ Generates an indicator list for the 'log' attribute of hyperparameters in the configuration space.
        """
        log_indicator = {}
        for hparam in list(self.configuration_space.values()):
            if hasattr(hparam, 'log'):
                log_indicator[hparam.name] = hparam.log
            else:
                log_indicator[hparam.name] = False
        self.log_indicator = [log_indicator[k] for k in self.configuration_names]

    def generate_categorical_indicator(self):
        """ Generates an indicator list for the categorical hyperparameters in the configuration space.
        """
        categorical_indicator = {}
        categories = {}
        for hparam in list(self.configuration_space.values()):
            if isinstance(hparam, CategoricalHyperparameter):
                categorical_indicator[hparam.name] = True
                categories[hparam.name] = hparam.choices
            else:
                categorical_indicator[hparam.name] = False
                categories[hparam.name] = []
        self.categorical_indicator = [categorical_indicator[k] for k in self.configuration_names]
        self.categories = [categories[k] for k in self.configuration_names]

    def get_log_indicator(self) -> List[bool]:
        """ Returns the log information of hyperparameters.
        """
        return self.log_indicator

    def get_categorical_indicator(self) -> Tuple[List[bool], List]:
        """ Returns the categorical information of hyperparameters.
        """
        return self.categorical_indicator, self.categories
