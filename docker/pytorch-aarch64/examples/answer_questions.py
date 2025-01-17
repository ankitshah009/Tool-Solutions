# *******************************************************************************
# Copyright 2021 Arm Limited and affiliates.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# *******************************************************************************

import sys
import random
import torch
from transformers import DistilBertTokenizer, DistilBertForQuestionAnswering

from utils import nlp_parser
from utils import nlp


def main():
    """
    Main function
    """

    # Parse cmd line arguments
    args = nlp_parser.parse_arguments()

    source = ""
    subject = ""
    context = ""
    question = ""
    answer = ""

    # Setup the question, either from a specified SQuAD record
    # or from cmd line arguments.
    # If no question details are provided, a random
    # SQuAD example will be chosen.
    if args["question"] is not None:
        question = args["question"]
        if args["text"] is not None:
            source = args["text"]
            with open(source, "r") as text_file_handle:
                context = text_file_handle.read()

        else:
            print("No text provided, searching SQuAD dev-2.0 dataset")
            squad_data = nlp.import_squad_data()
            squad_records = squad_data.loc[squad_data["question"] == question]
            if squad_records.empty:
                sys.exit(
                    "Question not found in SQuAD data, please provide context using `--text`."
                )
            subject = squad_records["subject"].iloc[0]
            context = squad_records["context"].iloc[0]
            question = squad_records["question"].iloc[0]
            answer = squad_records["answer"]

    else:
        squad_data = nlp.import_squad_data()

        if args["squadid"] is not None:
            source = args["squadid"]
            squad_records = squad_data.loc[squad_data["id"] == source]
            i_record = 0
        else:
            if args["subject"] is not None:
                print(
                    "Picking a question at random on the subject: ",
                    args["subject"],
                )
                squad_records = squad_data.loc[
                    squad_data["subject"] == args["subject"]
                ]
            else:
                print(
                    "No SQuAD ID or question provided, picking one at random!"
                )
                squad_records = squad_data

            n_records = len(squad_records.index)
            i_record = random.randint(0, max(0, n_records - 1))

        if squad_records.empty:
            sys.exit(
                "No questions found in SQuAD data, please provide valid ID or subject."
            )

        n_records = len(squad_records.index)
        i_record = random.randint(0, n_records - 1)
        source = squad_records["id"].iloc[i_record]
        subject = squad_records["subject"].iloc[i_record]
        context = squad_records["context"].iloc[i_record]
        question = squad_records["question"].iloc[i_record]
        answer = squad_records["answer"].iloc[i_record]

    # DistilBERT question answering using pre-trained model.
    token = DistilBertTokenizer.from_pretrained(
        "distilbert-base-uncased", return_token_type_ids=True
    )

    model = DistilBertForQuestionAnswering.from_pretrained(
        "distilbert-base-uncased-distilled-squad"
    )

    encoding = token.encode_plus(question, context)

    input_ids, attention_mask = (
        encoding["input_ids"],
        encoding["attention_mask"],
    )
    start_scores, end_scores = model(
        torch.tensor([input_ids]),
        attention_mask=torch.tensor([attention_mask]),
        return_dict=False,
    )

    answer_ids = input_ids[
        torch.argmax(start_scores) : torch.argmax(end_scores) + 1
    ]
    answer_tokens = token.convert_ids_to_tokens(
        answer_ids, skip_special_tokens=True
    )
    answer_tokens_to_string = token.convert_tokens_to_string(answer_tokens)

    # Display results
    print("\nDistilBERT question answering example.")
    print("======================================")
    print("Reading from: ", subject, source)
    print("\nContext: ", context)
    print("--")
    print("Question: ", question)
    print("Answer: ", answer_tokens_to_string)
    print("Reference Answers: ", answer)


if __name__ == "__main__":
    main()
