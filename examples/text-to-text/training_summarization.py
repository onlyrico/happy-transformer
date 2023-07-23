import csv
from happytransformer.happy_text_to_text import HappyTextToText, TTTrainArgs
from datasets import load_dataset

def main():
    happy_tt = HappyTextToText("T5", "t5-base")
    train_csv_path = "train.csv"
    eval_csv_path = "eval.csv"

    # source ; https://en.wikipedia.org/wiki/Transformer_(machine_learning_model)
    text = "A transformer is a deep learning model that adopts the mechanism of attention, differentially weighing the significance of each part of the input data. It is used primarily in the field of natural language processing (NLP)"
    before_text = happy_tt.generate_text("summarize: "+ text)

    train_dataset = load_dataset("xsum", split='train[0:1999]')
    eval_dataset = load_dataset("xsum", split='validation[0:499]')

    generate_csv(train_csv_path, train_dataset)
    generate_csv(eval_csv_path, eval_dataset)

    train_args = TTTrainArgs(max_input_length=1024,
                       max_output_length=128,
                       # deepspeed="ZERO-2",
                       # report_to = ('wandb')
                       )

    happy_tt.train(train_csv_path, args=train_args)
    after_text = happy_tt.generate_text("summarize: " + text)

    print("before text:", before_text)
    print("after text:", after_text)

def generate_csv(csv_path, dataset):
    with open(csv_path, 'w', newline='') as csvfile:
        writter = csv.writer(csvfile)
        writter.writerow(["input", "target"])
        for case in dataset:
            long_text = "summarize" + case["document"]
            short_text = case["summary"]
            writter.writerow([long_text, short_text])



if __name__ == "__main__":
    main()