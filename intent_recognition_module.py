# -*- coding: utf-8 -*-
import json
import re

import numpy as np
from scipy.spatial import distance
from transformers import GPT2LMHeadModel, GPT2Tokenizer


class Ir_Module:
    def __init__(self):
        self.threshold = 0.4
        self.model = GPT2LMHeadModel.from_pretrained("sberbank-ai/rugpt3small_based_on_gpt2")
        self.tokenizer = GPT2Tokenizer.from_pretrained("sberbank-ai/rugpt3small_based_on_gpt2")
        with open("training_corpus.json", encoding="utf8") as json_file:
            self.training_corpus = np.array(json.load(json_file))
            self.questions = [question[0] for question in self.training_corpus]
            self.question_embs = self.get_embeddings()

    def get_embeddings(self):
        question_embs = []
        for question in self.questions:
            question = self.tokenizer.encode(question)
            emb = sum([self.model.transformer.wte.weight[token, :] for token in question])
            question_embs.append(emb.detach().numpy())

        return question_embs

    def get_intent(self, question):
        question = question.lower()

        auth_key_present = re.match(r"\w{8}-\w{4}-\w{4}-\w{4}-\w{12}", question)
        if auth_key_present is not None:
            intent = "egrn_auth_key"
        else:
            question = re.sub(r"\d{2}:\d{2}:\d{1,7}:\d{1,}", "", question)
            print(question)
            tokenized_question = self.tokenizer.encode(question)
            sentence_vector = sum([self.model.transformer.wte.weight[token, :] for token in tokenized_question])
            sentence_vector = sentence_vector.detach().numpy()

            # calculating cosine distances to predefined questions and putting it into an array
            cosine_distances = np.empty(0)
            for emb in self.question_embs:
                cosine_distance = distance.cosine(sentence_vector, emb)
                cosine_distances = np.append(cosine_distances, cosine_distance)
            # calculating an index of the closest question
            result_idx = np.argmin(cosine_distances)
            # getting the appropriate answer from a list of predefined answers
            intent = self.training_corpus[result_idx][1]
            for dist in cosine_distances:
                print(dist)
            print(f"Min cosine distance: {min(cosine_distances)}")

            # if cosine distance is too big to all the questions, use text answering module instead
            if min(cosine_distances) == None or min(cosine_distances) > self.threshold:
                intent = "unknown"
        print(f"Intent: {intent}")

        return intent


ir = Ir_Module()

if __name__ == "__main__":
    pass
