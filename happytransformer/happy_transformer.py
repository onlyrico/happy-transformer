"""
Contains the parent class to HappyTextClassification, HappyWordPrediction, HappyQuestionAnswering
and HappyNextSentencePrediction called HappyTransformer

Contains shared variables and methods for these classes.
"""
import logging
from transformers import  AutoTokenizer, AutoConfig
from happytransformer.happy_trainer import  TrainArgs
import torch
from datasets import load_dataset, load_from_disk, DatasetDict

class HappyTransformer():
    """
    Parent class to HappyTextClassification, HappyWordPrediction, HappyQuestionAnswering
    and HappyNextSentencePrediction.

    """

    def __init__(self, model_type, model_name, model, load_path="", use_auth_token: str = None):
        self.model_type = model_type  # BERT, #DISTILBERT, ROBERTA, ALBERT etc
        self.model_name = model_name

        if load_path != "":
            self.tokenizer = AutoTokenizer.from_pretrained(load_path)
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_auth_token=use_auth_token)
        self.model = model
        self.model.eval()
        self._trainer = None  # initialized in child class

        # todo  change logging system
        self.logger = logging.getLogger(__name__)

        handler = logging.StreamHandler()
        handler.addFilter(logging.Filter('happytransformer'))
        logging.basicConfig(
            format='%(asctime)s - %(levelname)s - %(name)s -   %(message)s',
            datefmt='%m/%d/%Y %H:%M:%S',
            level=logging.INFO,
            handlers=[handler]
        )

        self.device = None

        if torch.backends.mps.is_available():
            if torch.backends.mps.is_built():
                self.device = torch.device("mps")

        if torch.cuda.is_available():
            self.device = torch.device("cuda:0")

        if not self.device:
            self.device = torch.device("cpu")

        if self.device.type != 'cpu':
            self.model.to(self.device)

        self.logger.info("Using model: %s", self.device)

        # Set within the child classes.
        self._data_collator = None
        self._t_data_file_type = None


    def train(self, input_filepath: str ,  args: TrainArgs, eval_filepath: str = "", ):
        """
        Trains a model
        :param input_filepath: A string that contains a path to a file that contains training data.
        :param input_filepath: A  string that contains a path to a file that contains eval data.
        :param args: A TrainArgs() child class such as GENTrainArgs()
        :return: None
        """
        if type(args) == dict:
            raise ValueError("Dictionary training arguments are no longer supported as of Happy Transformer version 2.5.0.")

        train_tok_data, eval_tok_data = self._preprocess_data(input_filepath=input_filepath,
                                                              eval_filepath=eval_filepath,
                                                              dataclass_args=args,
                                                              file_type=self._t_data_file_type)

        self._trainer._run_train(train_tok_data, eval_tok_data, args,  self._data_collator)



    def eval(self, input_filepath, args):
        """
        Evaluates the model. Determines how well the model performs on a given dataset
        :param input_filepath: a string that contains a path to a
         csv file that contains evaluating data
        :param args: settings in the form of a dictionary
        :return: correct percentage
        """
        if type(args) == dict:
            raise ValueError("Dictionary evaluating arguments are no longer supported as of Happy Transformer version 2.5.0.")

        return self._trainer.eval(input_filepath=input_filepath, dataclass_args=args)


    def test(self, input_filepath, args):
        """
        Used to generate predictions for a given dataset.
        The dataset may not be labelled.
        :param args: settings in the form of a dictionary

        :param input_filepath: a string that contains a path to
        a csv file that contains testing data

        """
        raise NotImplementedError()

    def save(self, path):
        """
        Saves both the model, tokenizer and various configuration/settings files
        to a given path

        :param path: string:  a path to a directory
        :return:
        """
        self.model.save_pretrained(path)
        self.tokenizer.save_pretrained(path)

    def _preprocess_data(self, input_filepath, eval_filepath, file_type, dataclass_args: TrainArgs):
        """
        :param input_filepath: A path to a training file.
        :param eval_filepath:  A path to an evaluating file. Or "" if not evaluating file is provided.
        :param file_type: The type of file: csv, text etc
        :param dataclass_args: A TrainArgs child class.
        :return:
        """

        if not dataclass_args.load_preprocessed_data:
            if eval_filepath == "":
                all_raw_data = load_dataset(file_type, data_files={"train": input_filepath}, split="train")
                all_raw_data = all_raw_data.shuffle(seed=42)
                split_text_data = all_raw_data.train_test_split(test_size=dataclass_args.eval_ratio)
                train_tok_data = self._tok_function(split_text_data["train"], dataclass_args)
                eval_tok_data = self._tok_function(split_text_data["test"], dataclass_args)
            else:
                raw_data = load_dataset(file_type, data_files={"train": input_filepath, "eval": eval_filepath})
                train_tok_data = self._tok_function(raw_data["train"], dataclass_args)
                eval_tok_data = self._tok_function( raw_data["eval"], dataclass_args)
        else:
            if dataclass_args.save_preprocessed_data_path.endswith(".json"):
                raise ValueError(
                    "As of version 2.5.0 preprocessed files are not longer saved as json files. Please preprocess your data again")

            self.logger.info("Loading dataset from %s...", dataclass_args.load_preprocessed_data_path)
            tok_data = load_from_disk(dataclass_args.load_preprocessed_data_path)
            train_tok_data = tok_data["train"]
            eval_tok_data = tok_data["eval"]

        if dataclass_args.save_preprocessed_data:

            if dataclass_args.load_preprocessed_data:
                self.logger.warning("Both save_preprocessed_data and load_data are enabled,")

            if dataclass_args.save_preprocessed_data_path.endswith(".json"):
                raise ValueError(
                    "As of version 2.5.0 preprocessed files are not longer saved as json files. Please provide a path to a folder.")


            combined_tok = DatasetDict({"train": train_tok_data, "eval": eval_tok_data})
            combined_tok.save_to_disk(dataclass_args.save_preprocessed_data_path)

        return train_tok_data, eval_tok_data


    def _tok_function(self, raw_dataset, dataclass_args: TrainArgs):
        raise NotImplementedError()