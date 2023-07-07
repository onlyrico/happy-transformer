"""

Fine-tuning for text generation models.

Based on the tutorial found here:
https://github.com/huggingface/transformers/blob/master/examples/pytorch/language-modeling/run_clm.py
"""
from dataclasses import dataclass
from transformers import default_data_collator
from happytransformer.happy_trainer import HappyTrainer, EvalResult
from happytransformer.fine_tuning_util import preprocess_concatenate
from happytransformer.gen.default_args import ARGS_GEN_TRAIN, ARGS_GEN_EVAl
from datasets import load_dataset, load_from_disk, DatasetDict
from happytransformer.happy_trainer import TrainArgs

@dataclass
class GENTrainArgs(TrainArgs):
    save_preprocessed_data: bool = ARGS_GEN_TRAIN["save_preprocessed_data"]
    save_preprocessed_data_path: str = ARGS_GEN_TRAIN["save_preprocessed_data_path"]
    load_preprocessed_data: bool = ARGS_GEN_TRAIN["load_preprocessed_data"]
    load_preprocessed_data_path: str = ARGS_GEN_TRAIN["load_preprocessed_data_path"]
    preprocessing_processes: int = ARGS_GEN_TRAIN["preprocessing_processes"]
    mlm_probability: float = ARGS_GEN_TRAIN["mlm_probability"]


@dataclass
class GENEvalArgs:
    batch_size: int = ARGS_GEN_EVAl["batch_size"]
    save_preprocessed_data: bool = ARGS_GEN_EVAl["save_preprocessed_data"]
    save_preprocessed_data_path: str = ARGS_GEN_EVAl["save_preprocessed_data_path"]
    load_preprocessed_data: bool = ARGS_GEN_EVAl["load_preprocessed_data"]
    load_preprocessed_data_path: str = ARGS_GEN_EVAl["load_preprocessed_data_path"]
    preprocessing_processes: int =ARGS_GEN_EVAl["preprocessing_processes"]
    mlm_probability: float = ARGS_GEN_EVAl["mlm_probability"]


class GENTrainer(HappyTrainer):
    """
    Trainer class for HappyWordPrediction
    """

    def eval(self, input_filepath, dataclass_args: GENEvalArgs):
        """
        :param input_filepath: A file path to a text file that contains nothing but evaluating data
        :param dataclass_args: A GENEvalArgs() object
        :return: An EvalResult() object
        """

        if not dataclass_args.load_preprocessed_data:
            self.logger.info("Preprocessing dataset...")
            datasets = load_dataset("text", data_files={"eval": input_filepath})
            tokenized_dataset = preprocess_concatenate(self.tokenizer, datasets, dataclass_args.preprocessing_processes, False)

        else:
            self.logger.info("Loading dataset from %s...", dataclass_args.load_preprocessed_data_path)
            tokenized_dataset = load_from_disk(dataclass_args.load_preprocessed_data_path +"/eval")

        if dataclass_args.save_preprocessed_data:
            if dataclass_args.load_preprocessed_data:
                self.logger.warning("Both save_preprocessed_data and load_data are enabled.")

            self.logger.info("Saving evaluating dataset to %s...", dataclass_args.save_preprocessed_data_path)
            save_dataset = DatasetDict({"eval": tokenized_dataset})
            save_dataset.save_to_disk(dataclass_args.save_preprocessed_data_path)

        self.logger.info("Evaluating...")
        result = self._run_eval(tokenized_dataset["eval"], default_data_collator, dataclass_args)
        return EvalResult(loss=result["eval_loss"])

    def test(self, input_filepath, solve, args):
        raise NotImplementedError()

