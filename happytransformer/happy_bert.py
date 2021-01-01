"""
HappyBERT: a wrapper over PyTorch's BERT implementation

"""

# disable pylint TODO warning
# pylint: disable=W0511
import re
from transformers import (
    BertForMaskedLM,
    BertForNextSentencePrediction,
    BertForQuestionAnswering,
    BertTokenizerFast

)

import torch
from happytransformer.runners.runner_answer_question import AnswerQuestionRunner

from happytransformer.happy_transformer import HappyTransformer
from happytransformer.trainers.trainer_qa import QATrainer

class HappyBERT(HappyTransformer):
    """
    Currently available public methods:
        BertForMaskedLM:
            1. predict_mask(text: str, options=None, k=1)
        BertForSequenceClassification:
            1. init_sequence_classifier()
            2. advanced_init_sequence_classifier()
            3. train_sequence_classifier(train_csv_path)
            4. eval_sequence_classifier(eval_csv_path)
            5. test_sequence_classifier(test_csv_path)
        BertForNextSentencePrediction:
            1. predict_next_sentence(sentence_a, sentence_b)
        BertForQuestionAnswering:
            1. answer_question(question, text)

            """

    def __init__(self, model='bert-base-uncased'):
        # todo remove model parameter. Each model will have its own
        super().__init__(model, "BERT")
        self.mlm = None  # Masked Language Model
        self.nsp = None  # Next Sentence Prediction

        #todo separate tokenizer for each model
        self.tokenizer = BertTokenizerFast.from_pretrained("bert-base-uncased")
        self.masked_token = self.tokenizer.mask_token
        self.sep_token = self.tokenizer.sep_token
        self.cls_token = self.tokenizer.cls_token

        # ------------------------ QA
        self.__qa_model = None   # Question Answering
        self.__qa_tokenizer = None

        self.__qa_init = False
        self.__qa_trainer = None
        self.__qa_runner = None

    def _get_masked_language_model(self):
        """
        Initializes the BertForMaskedLM transformer
        """
        self.mlm = BertForMaskedLM.from_pretrained(self.model)
        self.mlm.eval()

    def _get_next_sentence_prediction(self):
        """
        Initializes the BertForNextSentencePrediction transformer
        """
        self.nsp = BertForNextSentencePrediction.from_pretrained(self.model)
        self.nsp.eval()




    def predict_next_sentence(self, sentence_a, sentence_b, use_probability=False):
        """
        Determines if sentence B is likely to be a continuation after sentence
        A.
        :param sentence_a: First sentence
        :param sentence_b: Second sentence to test if it comes after the first
        :param use_probability: Toggle outputting probability instead of boolean
        :return Result of whether sentence B follows sentence A,
                as either a probability or a boolean
        """

        if not self.__is_one_sentence(sentence_a) or not self.__is_one_sentence(sentence_b):
            self.logger.error('Each inputted text variable for the "predict_next_sentence" method must contain a single sentence')
            exit()

        if self.nsp is None:
            self._get_next_sentence_prediction()

        if self.gpu_support == 'cuda':
            self.nsp.to('cuda')

        connected = sentence_a + ' ' + sentence_b
        tokenized_text = self._get_tokenized_text(connected)
        indexed_tokens = self.tokenizer.convert_tokens_to_ids(tokenized_text)
        segments_ids = self._get_segment_ids(tokenized_text)
        # Convert inputs to PyTorch tensors
        tokens_tensor = torch.tensor([indexed_tokens])
        segments_tensors = torch.tensor([segments_ids])
        with torch.no_grad():
            predictions = self.nsp(tokens_tensor, token_type_ids=segments_tensors)[0]

        probabilities = torch.nn.Softmax(dim=1)(predictions)
        # probability that sentence B follows sentence A
        correct_probability = probabilities[0][0].item()

        if self.gpu_support == 'cuda':
            torch.cuda.empty_cache()

        return (
            correct_probability if use_probability else 
            correct_probability >= 0.5
        )

    def __is_one_sentence(self, text):
        """
        Used to verify the proper input requirements for sentence_relation.
        The text must contain no more than a single sentence.
        Casual use of punctuation is accepted, such as using multiple exclamation marks.
        :param text: A body of text
        :return: True if the body of text contains a single sentence, else False
        """
        split_text = re.split('[?.!]', text)
        sentence_found = False
        for possible_sentence in split_text:
            for char in possible_sentence:
                if char.isalpha():
                    if sentence_found:
                        return False
                    sentence_found = True
                    break
        return True
#-------------------------------------------------------#

                # QUESTION ANSWERING #
#-------------------------------------------------------#

    def init_qa(self, model='bert-large-uncased-whole-word-masking-finetuned-squad'):
        """
        Initializes the BertForQuestionAnswering transformer
        NOTE: This uses the bert-large-uncased-whole-word-masking-finetuned-squad pretraining for best results.
        """
        self.__qa_model = BertForQuestionAnswering.from_pretrained(model)
        self.__qa_tokenizer = BertTokenizerFast.from_pretrained(model)
        self.__qa_model.eval()

        if self.gpu_support == 'cuda':
            self.__qa_model.to('cuda')

        self.__qa_runner = AnswerQuestionRunner(self._model_name, self.__qa_model, self.__qa_tokenizer)
        self.__qa_init = True

    def answers_to_question(self, question, context, k=3):
        if self.__qa_init:
            return self.__qa_runner.run_answers_to_question(question, context, k=k)
        else:
            self._init_model_first_warning("question answering", "init_qa(model_name)")


    def answer_question(self, question, text):
        """
        Using the given text, find the answer to the given question and return it.

        :param question: The question to be answered
        #todo breaking change: change text to context
        :param text: The text containing the answer to the question
        :return: The answer to the given question, as a string
        """
        if self.__qa_init:
            return self.__qa_runner.run_answer_question(question, text)
        else:
            self._init_model_first_warning("question answering", "init_qa(model_name)")

    def train_qa(self, filepath, args=None):
        if self.__qa_init:
            if self.__qa_trainer==None:
                # model, model_name, tokenizer, args, model_type, device, runne
                self.__qa_trainer = QATrainer(self.__qa_model, "bert", self.tokenizer,  self.gpu_support, self.__qa_runner, self.logger)

            self.__qa_trainer.train(filepath, args)
        else:
            self._init_model_first_warning("question answering", "init_qa(model_name)")

    def test_qa(self, filepath, args=None):
        if self.__qa_init:
            if self.qa_trainer == None:
                self.qa_trainer = QATrainer(self.__qa_model, "bert", self.tokenizer, self.gpu_support, self.__qa_runner, self.logger)

            self.__qa_trainer.train(filepath, args)
        else:
            self._init_model_first_warning("question answering", "init_qa(model_name)")

    def eval_qa(self, filepath, output_filepath=None, args=None):
        if self.__qa_init:
            if self.__qa_trainer == None:
                self.__qa_trainer = QATrainer(self.__qa_model, "bert", self.tokenizer, self.gpu_support,  self.__qa_runner, self.logger)

            return self.__qa_trainer.eval(filepath, args, output_filepath)
        else:
            self._init_model_first_warning("question answering", "init_qa(model_name)")
            return - 1
