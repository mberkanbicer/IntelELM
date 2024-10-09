#!/usr/bin/env python
# Created by "Thieu" at 9:23 PM, 08/10/2024 --------%                                                                               
#       Email: nguyenthieu2102@gmail.com            %                                                    
#       Github: https://github.com/thieu1995        %                         
# --------------------------------------------------%

import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional
from sklearn.base import BaseEstimator
from permetrics import RegressionMetric, ClassificationMetric
from mealpy import get_optimizer_by_name, Optimizer, get_all_optimizers, FloatVar
from intelelm.utils import activation, validator
from intelelm.utils.evaluator import get_all_regression_metrics, get_all_classification_metrics


class MultiLayerELM:
    """
    Initializes the Multi-Layer ELM model.

    Parameters
    ----------
    layer_sizes : list of int
        List of integers, where each integer represents the number of neurons in the respective hidden layers.
    act_name : str, optional
        Activation function to be used in the hidden layers ("relu", "leaky_relu", "celu", "prelu", "gelu",
        "elu", "selu", "rrelu", "tanh", "hard_tanh", "sigmoid", "hard_sigmoid", "log_sigmoid", "silu",
        "swish", "hard_swish", "soft_plus", "mish", "soft_sign", "tanh_shrink", "soft_shrink",
        "hard_shrink", "softmin", "softmax", "log_softmax"). Default is 'relu'.
    seed : int, optional
        Seed for random number generator. Default is None.
    """
    def __init__(self, layer_sizes=(10, ), act_name='relu', seed=None):
        """
        Initializes the Multi-Layer ELM model.

        Parameters:
        - layer_sizes: List of integers, where each integer represents the number of neurons in the respective hidden layers. Default is (10, )
        - act_name: Activation function to be used in the hidden layers. Default is 'relu'.
        """
        self.layer_sizes = layer_sizes
        self.act_name = act_name
        self.act_func = getattr(activation, self.act_name)
        self.generator = np.random.default_rng(seed)
        self.weights = []
        self.biases = []
        self.beta = None
        self.input_size, self.obj_scaler = None, None

    def _initialize_weights(self, input_size):
        self.weights = []
        self.biases = []
        for size in self.layer_sizes:
            weight = self.generator.standard_normal(size=(input_size, size))
            bias = self.generator.standard_normal(size)
            self.weights.append(weight)
            self.biases.append(bias)
            input_size = size

    def _forward(self, X):
        # Forward pass through multiple layers
        for i in range(len(self.layer_sizes)):
            X = self.act_func(np.dot(X, self.weights[i]) + self.biases[i])
        return X

    def fit(self, X, y):
        """Fit the model to data matrix X and target(s) y.

        Parameters
        ----------
        X : ndarray or sparse matrix of shape (n_samples, n_features)
            The input data.

        y : ndarray of shape (n_samples,) or (n_samples, n_outputs)
            The target values (class labels in classification, real numbers in regression).

        Returns
        -------
        self : object
            Returns a trained ELM model.
        """

        # Initialize random weights for each layer
        self.input_size = X.shape[1]
        self._initialize_weights(input_size=self.input_size)
        # Forward pass to compute hidden layer output
        H = self._forward(X)
        # Compute output weights (beta) using Moore-Penrose pseudoinverse
        self.beta = np.dot(np.linalg.pinv(H), y)
        return self

    def predict(self, X):
        """Predict using the Extreme Learning Machine model.

        Parameters
        ----------
        X : {array-like, sparse matrix} of shape (n_samples, n_features)
            The input data.

        Returns
        -------
        y : ndarray of shape (n_samples, n_outputs)
            The predicted values.
        """
        H = self._forward(X)
        return np.dot(H, self.beta)

    def encode(self):
        """
        Encode the current weights and biases into a 1-D vector (solution vector).

        Returns:
        - A 1-D numpy array containing all the weights and biases of the network.
        """
        flat_weights = [w.flatten() for w in self.weights]  # Flatten each weight matrix
        flat_biases = [b.flatten() for b in self.biases]  # Flatten each bias vector
        solution_vector = np.concatenate(flat_weights + flat_biases)  # Concatenate all into a 1-D vector
        return solution_vector

    def decode(self, solution_vector, X, y):
        """
        Decode a 1-D solution vector into the weights and biases of the network.

        Parameters:
        - solution_vector: 1-D numpy array containing the flattened weights and biases.
        """
        start = 0
        input_size = self.input_size
        self.weights = []
        self.biases = []

        # Decode weights and biases for each layer
        for i, size in enumerate(self.layer_sizes):
            weight_size = input_size * size
            bias_size = size

            # Extract the weights and reshape them to the correct matrix shape
            weight = solution_vector[start:start + weight_size].reshape((input_size, size))
            self.weights.append(weight)
            start += weight_size

            # Extract the biases
            bias = solution_vector[start:start + bias_size]
            self.biases.append(bias)
            start += bias_size

            input_size = size

        # Update beta
        H = self._forward(X)
        self.beta = np.dot(np.linalg.pinv(H), y)

    def get_ndim(self):
        """
        Get the total number of dimensions (weights + biases) in the network.

        Returns:
        - An integer representing the total number of parameters (weights + biases).
        """
        total_params = 0
        input_size = self.input_size
        for i, size in enumerate(self.layer_sizes):
            total_params += input_size * size  # Add weights
            total_params += size  # Add biases
            input_size = size
        return total_params

    def get_weights(self):
        print( [w.shape for w in self.weights])
        print(self.beta.shape)
        return {
            "w": self.weights,
            "b": self.biases,
            "beta": self.beta
        }


class BaseElm(BaseEstimator):
    """
    class BaseElm(BaseEstimator):
        A base class for implementing Extreme Learning Machines (ELM) with support for both classification and regression tasks.

        Attributes
        ----------
        layer_sizes : list
            List containing the sizes of each layer in the network.

        act_name : str
            The name of the activation function to be used.

        network : object
            The ELM network object.

        loss_train : list
            List of loss values recorded during training.

        n_labels : int
            Number of labels in the dataset.
    """

    SUPPORTED_CLS_METRICS = get_all_classification_metrics()
    SUPPORTED_REG_METRICS = get_all_regression_metrics()
    CLS_OBJ_LOSSES = None

    def __init__(self, layer_sizes=(10, ), act_name='relu'):
        super().__init__()
        # Directly assign layer_sizes without modification
        if not isinstance(layer_sizes, (list, tuple, np.ndarray, int)):
            raise ValueError(f"layer_sizes should be an int, list, tuple, or np.ndarray. Got {type(layer_sizes)}")
        self.layer_sizes = layer_sizes if isinstance(layer_sizes, (list, tuple, np.ndarray)) else [layer_sizes]
        self.act_name = act_name
        self.network, self.loss_train, self.n_labels, self.input_size = None, None, None, None

    @staticmethod
    def _check_method(method=None, list_supported_methods=None):
        if type(method) is str:
            return validator.check_str("method", method, list_supported_methods)
        else:
            raise ValueError(f"method should be a string and belongs to {list_supported_methods}")

    def get_weights(self):
        """
        Retrieves the current weights of the neural network.

        Returns
        -------
        list
            A list containing the weights of the neural network.
        """
        return self.network.get_weights()

    def create_network(self, X, y) -> Optional["MultiLayerELM"]:
        """
        Parameters
        ----------
        X : ndarray
            Input data used to train the network.
        y : ndarray
            Target values corresponding to the input data X.

        Returns
        -------
        Optional["MultiLayerELM"]
            Returns an instance of the MultiLayerELM class if creation is successful, otherwise, returns None.
        """
        return None

    def fit(self, X, y):
        """
        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            Training data.

        y : array-like of shape (n_samples,) or (n_samples, n_outputs)
            Target values.
        """
        self.network = self.create_network(X, y)
        y_scaled = self.network.obj_scaler.transform(y)
        self.network.fit(X, y_scaled)
        return self

    def predict(self, X, return_prob=False):
        """
        Inherit the predict function from BaseElm class, with 1 more parameter `return_prob`.

        Parameters
        ----------
        X : {array-like, sparse matrix} of shape (n_samples, n_features)
            The input data.

        return_prob : bool, default=False
            It is used for classification problem:

            - If True, the returned results are the probability for each sample
            - If False, the returned results are the predicted labels
        """
        pred = self.network.predict(X)
        if return_prob:
            return pred
        return self.network.obj_scaler.inverse_transform(pred)

    def __evaluate_reg(self, y_true, y_pred, list_metrics=("MSE", "MAE")):
        """
        Parameters
        ----------
        y_true : array-like
            Ground truth (correct) target values.
        y_pred : array-like
            Estimated target values.
        list_metrics : tuple/list of str, optional
            List of metric names to evaluate. Default is ("MSE", "MAE").
        """
        rm = RegressionMetric(y_true=y_true, y_pred=y_pred)
        return rm.get_metrics_by_list_names(list_metrics)

    def __evaluate_cls(self, y_true, y_pred, list_metrics=("AS", "RS")):
        """
        Parameters
        ----------
        y_true : array-like of shape (n_samples,)
            True class labels.
        y_pred : array-like of shape (n_samples,)
            Predicted class labels by the classifier.
        list_metrics : tuple/list of str, optional
            List of metric names to evaluate, by default ("AS", "RS").
        """
        cm = ClassificationMetric(y_true, y_pred)
        return cm.get_metrics_by_list_names(list_metrics)

    def __score_reg(self, X, y, method="RMSE"):
        """
        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            The input samples used for prediction.

        y : array-like of shape (n_samples,)
            The true target values.

        method : str, optional, default="RMSE"
            The regression metric to be used for scoring. Must be one of the supported metrics in SUPPORTED_REG_METRICS.

        Returns
        -------
        float
            The calculated regression metric based on the method provided.

        """
        method = self._check_method(method, list(self.SUPPORTED_REG_METRICS.keys()))
        y_pred = self.network.predict(X)
        return RegressionMetric(y, y_pred).get_metric_by_name(method)[method]

    def __scores_reg(self, X, y, list_methods=("MSE", "MAE")):
        """
        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            Input data.

        y : array-like of shape (n_samples,)
            True values for X.

        list_methods : tuple of str, optional
            List of evaluation metrics to be used. Default is ("MSE", "MAE").
        """
        y_pred = self.network.predict(X)
        return self.__evaluate_reg(y_true=y, y_pred=y_pred, list_metrics=list_methods)

    def __score_cls(self, X, y, method="AS"):
        """
        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            Test samples to score.

        y : array-like of shape (n_samples,)
            True labels for X.

        method : str, default="AS"
            Scoring method to use. Supported methods are determined by the keys in self.SUPPORTED_CLS_METRICS.

        Returns
        -------
        float
            Computed score based on the specified method.
        """
        method = self._check_method(method, list(self.SUPPORTED_CLS_METRICS.keys()))
        return_prob = False
        if self.n_labels > 2:
            if method in self.CLS_OBJ_LOSSES:
                return_prob = True
        y_pred = self.predict(X, return_prob=return_prob)
        cm = ClassificationMetric(y_true=y, y_pred=y_pred)
        return cm.get_metric_by_name(method)[method]

    def __scores_cls(self, X, y, list_methods=("AS", "RS")):
        """
        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            Feature matrix for the samples for which predictions are to be made.

        y : array-like of shape (n_samples,)
            True labels for the samples.

        list_methods : tuple of str, optional
            List of method names to evaluate. Possible values include 'AS', 'RS', etc. Default is ('AS', 'RS').

        Returns
        -------
        dict
            A dictionary with the performance metrics from the selected methods listed in `list_methods`.
        """
        list_errors = list(set(list_methods) & set(self.CLS_OBJ_LOSSES))
        list_scores = list((set(self.SUPPORTED_CLS_METRICS.keys()) - set(self.CLS_OBJ_LOSSES)) & set(list_methods))
        t1 = {}
        if len(list_errors) > 0:
            return_prob = False
            if self.n_labels > 2:
                return_prob = True
            y_pred = self.predict(X, return_prob=return_prob)
            t1 = self.__evaluate_cls(y_true=y, y_pred=y_pred, list_metrics=list_errors)
        y_pred = self.predict(X, return_prob=False)
        t2 = self.__evaluate_cls(y_true=y, y_pred=y_pred, list_metrics=list_scores)
        return {**t2, **t1}

    def evaluate(self, y_true, y_pred, list_metrics=None):
        """Return the list of performance metrics of the prediction.

        Parameters
        ----------
        y_true : array-like of shape (n_samples,) or (n_samples, n_outputs)
            True values for `X`.

        y_pred : array-like of shape (n_samples,) or (n_samples, n_outputs)
            Predicted values for `X`.

        list_metrics : list
            You can get metrics from Permetrics library: https://github.com/thieu1995/permetrics

        Returns
        -------
        results : dict
            The results of the list metrics
        """
        pass

    def score(self, X, y, method=None):
        """Return the metric of the prediction.

        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            Test samples. For some estimators this may be a precomputed kernel matrix or a list of generic objects instead with shape
            ``(n_samples, n_samples_fitted)``, where ``n_samples_fitted`` is the number of samples used in the fitting for the estimator.

        y : array-like of shape (n_samples,) or (n_samples, n_outputs)
            True values for `X`.

        method : str, default="RMSE"
            You can get metrics from Permetrics library: https://github.com/thieu1995/permetrics

        Returns
        -------
        result : float
            The result of selected metric
        """
        pass

    def scores(self, X, y, list_methods=None):
        """Return the list of metrics of the prediction.

        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            Test samples. For some estimators this may be a precomputed kernel matrix or a list of generic objects instead with shape
            ``(n_samples, n_samples_fitted)``, where ``n_samples_fitted`` is the number of samples used in the fitting for the estimator.

        y : array-like of shape (n_samples,) or (n_samples, n_outputs)
            True values for `X`.

        list_methods : list, default=("MSE", "MAE")
            You can get metrics from Permetrics library: https://github.com/thieu1995/permetrics

        Returns
        -------
        results : dict
            The results of the list metrics
        """
        pass

    def save_loss_train(self, save_path="history", filename="loss.csv"):
        """
        Save the loss (convergence) during the training process to csv file.

        Parameters
        ----------
        save_path : saved path (relative path, consider from current executed script path)
        filename : name of the file, needs to have ".csv" extension
        """
        Path(save_path).mkdir(parents=True, exist_ok=True)
        if self.loss_train is None:
            print(f"{self.__class__.__name__} model doesn't have training loss!")
        else:
            data = {"epoch": list(range(1, len(self.loss_train) + 1)), "loss": self.loss_train}
            pd.DataFrame(data).to_csv(f"{save_path}/{filename}", index=False)

    def save_metrics(self, y_true, y_pred, list_metrics=("RMSE", "MAE"), save_path="history", filename="metrics.csv"):
        """
        Save evaluation metrics to csv file

        Parameters
        ----------
        y_true : ground truth data
        y_pred : predicted output
        list_metrics : list of evaluation metrics
        save_path : saved path (relative path, consider from current executed script path)
        filename : name of the file, needs to have ".csv" extension
        """
        Path(save_path).mkdir(parents=True, exist_ok=True)
        results = self.evaluate(y_true, y_pred, list_metrics)
        df = pd.DataFrame.from_dict(results, orient='index').T
        df.to_csv(f"{save_path}/{filename}", index=False)

    def save_y_predicted(self, X, y_true, save_path="history", filename="y_predicted.csv"):
        """
        Save the predicted results to csv file

        Parameters
        ----------
        X : The features data, nd.ndarray
        y_true : The ground truth data
        save_path : saved path (relative path, consider from current executed script path)
        filename : name of the file, needs to have ".csv" extension
        """
        Path(save_path).mkdir(parents=True, exist_ok=True)
        y_pred = self.predict(X, return_prob=False)
        data = {"y_true": np.squeeze(np.asarray(y_true)), "y_pred": np.squeeze(np.asarray(y_pred))}
        pd.DataFrame(data).to_csv(f"{save_path}/{filename}", index=False)

    def save_model(self, save_path="history", filename="model.pkl"):
        """
        Save model to pickle file

        Parameters
        ----------
        save_path : saved path (relative path, consider from current executed script path)
        filename : name of the file, needs to have ".pkl" extension
        """
        Path(save_path).mkdir(parents=True, exist_ok=True)
        if filename[-4:] != ".pkl":
            filename += ".pkl"
        pickle.dump(self, open(f"{save_path}/{filename}", 'wb'))

    @staticmethod
    def load_model(load_path="history", filename="model.pkl"):
        """
        Parameters
        ----------
        load_path : str, optional
            Directory path where the model file is located. Defaults to "history".
        filename : str
            Name of the file to be loaded. If the filename doesn't end with ".pkl", the extension is automatically added.

        Returns
        -------
        object
            The model loaded from the specified pickle file.
        """
        if filename[-4:] != ".pkl":
            filename += ".pkl"
        return pickle.load(open(f"{load_path}/{filename}", 'rb'))


class BaseMhaElm(BaseElm):
    """
    BaseMhaElm Class
    ================
    The `BaseMhaElm` class is an optimization-based extension of the `BaseElm` class, designed for
    flexible optimization and parameter tuning of networks utilizing various optimizers from the
    Mealpy library. It supports different activation functions, objectives, and optimization strategies.

    Attributes
    ----------
    SUPPORTED_OPTIMIZERS : list
        List of supported optimizers, obtained from the Mealpy library.

    SUPPORTED_CLS_OBJECTIVES : dict
        Dictionary of supported classification objectives.

    SUPPORTED_REG_OBJECTIVES : dict
        Dictionary of supported regression objectives.

    Methods
    -------
    __init__(layer_sizes=None, act_name="elu", obj_name=None, optim="BaseGA", optim_paras=None, seed=None, verbose=True)
        Initializes the `BaseMhaElm` with specified parameters.

    get_name()
        Returns the name of the optimizer used, appended with `-ELM`.

    set_params(**params)
        Sets the parameters for the optimizer and updates parent class parameters.

    set_optimizer(optim)
        Sets the optimizer attribute.

    set_optim_paras(optim_paras)
        Sets the optimizer parameters attribute.

    set_optimizer_object(optim=None, optim_paras=None)
        Sets the optimizer object with the specified parameters.

    set_seed(seed)
        Sets the random seed for the class.

    _get_history_loss(optimizer=None)
        Retrieves the historical loss values from the optimizer.

    fitness_function(solution=None)
        Placeholder fitness function to be overridden by the subclass or user.

    _get_lb_ub(lb=None, ub=None, problem_size=None)
        Computes the lower and upper bounds based on the provided inputs and problem size.

    _get_minmax(obj_name=None)
        Retrieves the minmax value for the specified objective name.

    fit(X, y, lb=(-10.0, ), ub=(10.0, ), mode="single", n_workers=None, termination=None, save_population=False)
        Fits the model to the provided data using the specified optimization parameters.
    """
    SUPPORTED_OPTIMIZERS = list(get_all_optimizers().keys())
    SUPPORTED_CLS_OBJECTIVES = get_all_classification_metrics()
    SUPPORTED_REG_OBJECTIVES = get_all_regression_metrics()

    def __init__(self, layer_sizes=(10, ), act_name="elu",
                 obj_name=None, optim="BaseGA", optim_paras=None, seed=None, verbose=True):
        super().__init__(layer_sizes=layer_sizes, act_name=act_name)
        self.obj_name = obj_name
        if optim_paras is None:
            optim_paras = {"epoch": 500, "pop_size": 20}
        self.optim_paras = optim_paras
        self.optim = optim
        self.verbose = verbose
        self.seed = seed
        self.network, self.obj_weights = None, None

    def get_name(self):
        if type(self.optim) is str:
            return f"{self.optim_paras}-ELM"
        return f"{self.optimizer.name}-ELM"

    def set_params(self, **params):
        # Handle nested parameters for the optimizer
        optimizer_params = {k.split('__')[1]: v for k, v in params.items() if k.startswith('optim_paras__')}

        if optimizer_params:
            self.optim_paras.update(optimizer_params)

        # Pass non-optimizer parameters to the parent class set_params
        super_params = {k: v for k, v in params.items() if not k.startswith('optim_paras__')}
        super().set_params(**super_params)

        return self

    def set_optimizer(self, optim):
        self.optimizer = optim

    def set_optim_paras(self, optim_paras):
        self.optim_paras = optim_paras

    def set_optimizer_object(self, optim=None, optim_paras=None):
        """
        Parameters
        ----------
        optim : str or Optimizer
            The optim can be a string indicating the name of the optimizer supported by the Mealpy library
            or an instance of the Optimizer class.

        optim_paras : dict, optional
            A dictionary containing the hyper-parameters for the optimizer. This is only used if the optim
            parameter is provided either as a string or an Optimizer instance that supports parameter configuration.
        """
        if type(optim) is str:
            opt_class = get_optimizer_by_name(optim)
            if type(optim_paras) is dict:
                self.optim_paras = optim_paras
                self.optimizer = opt_class(**optim_paras)
            else:
                raise TypeError(f"optim_paras is a dictionary contains the hyper-parameter of optimizer in Mealpy library.")
        elif isinstance(optim, Optimizer):
            if type(optim_paras) is dict:
                self.optim_paras = optim_paras
                optim.set_parameters(optim_paras)
            self.optimizer = optim
        else:
            raise TypeError(f"optimizer needs to set as a string and supported by Mealpy library.")

    def set_seed(self, seed):
        """
        Parameters
        ----------
        seed : int
            The seed value to initialize the random number generator.
        """
        self.seed = seed

    def _get_history_loss(self, optimizer=None):
        list_global_best = optimizer.history.list_global_best
        # 2D array / matrix 2D
        global_obj_list = np.array([agent.target.objectives for agent in list_global_best])
        # Make each obj_list as an element in array for drawing
        return global_obj_list[:, 0]

    def fitness_function(self, solution=None):
        pass

    def _get_lb_ub(self, lb=None, ub=None, problem_size=None):
        if type(lb) in (list, tuple, np.ndarray) and type(ub) in (list, tuple, np.ndarray):
            if len(lb) == len(ub):
                if len(lb) == 1:
                    lb = np.array(lb * problem_size, dtype=float)
                    ub = np.array(ub * problem_size, dtype=float)
                elif len(lb) != problem_size:
                    raise ValueError(f"Invalid lb and ub. Their length should be equal to 1 or problem_size.")
            else:
                raise ValueError(f"Invalid lb and ub. They should have the same length.")
        elif type(lb) in (int, float) and type(ub) in (int, float):
            lb = (float(lb), ) * problem_size
            ub = (float(ub), ) * problem_size
        else:
            raise ValueError(f"Invalid lb and ub. They should be a number of list/tuple/np.ndarray with size equal to problem_size")
        return lb, ub

    def _get_minmax(self, obj_name=None):
        if obj_name is None:
            raise ValueError("obj_name can't be None")
        else:
            if obj_name in self.SUPPORTED_REG_OBJECTIVES.keys():
                minmax = self.SUPPORTED_REG_OBJECTIVES[obj_name]
            elif obj_name in self.SUPPORTED_CLS_OBJECTIVES.keys():
                minmax = self.SUPPORTED_CLS_OBJECTIVES[obj_name]
            else:
                raise ValueError("obj_name is not supported. Please check the library: permetrics to see the supported objective function.")
        return minmax

    def fit(self, X, y, lb=(-10.0, ), ub=(10.0, ), mode="single", n_workers=None, termination=None, save_population=False):
        """
        Parameters
        ----------
        X : The features data, np.ndarray
        y : The ground truth data
        lb : The lower bound for decision variables in optimization problem (The weights and biases of network)
        ub : The upper bound for decision variables in optimization problem (The weights and biases of network)
        mode: Parallel: 'process', 'thread'; Sequential: 'swarm', 'single'.

                * 'process': The parallel mode with multiple cores run the tasks
                * 'thread': The parallel mode with multiple threads run the tasks
                * 'swarm': The sequential mode that no effect on updating phase of other agents
                * 'single': The sequential mode that effect on updating phase of other agents, this is default mode

        n_workers: The number of workers (cores or threads) to do the tasks (effect only on parallel mode)
        termination: The termination dictionary or an instance of Termination class in Mealpy library
        save_population : Save the population of search agents (Don't set it to True when you don't know how to use it)
        """
        self.network = self.create_network(X, y)
        y_scaled = self.network.obj_scaler.transform(y)
        self.X_temp, self.y_temp = X, y_scaled
        problem_size = self.network.get_ndim()
        lb, ub = self._get_lb_ub(lb, ub, problem_size)
        minmax = self._get_minmax(self.obj_name)
        log_to = "console" if self.verbose else "None"
        problem = {
            "obj_func": self.fitness_function,
            "bounds": FloatVar(lb=lb, ub=ub),
            "minmax": minmax,
            "log_to": log_to,
            "save_population": save_population,
            "obj_weights": self.obj_weights
        }
        self.set_optimizer_object(self.optim, self.optim_paras)
        g_best = self.optimizer.solve(problem, mode=mode, n_workers=n_workers, termination=termination, seed=self.seed)
        self.solution, self.best_fit = g_best.solution, g_best.target.fitness
        self.network.decode(self.solution, self.X_temp, self.y_temp)
        self.loss_train = self._get_history_loss(optimizer=self.optimizer)
        return self
