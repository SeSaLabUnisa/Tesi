from string import punctuation
import spacy

import numpy as np

from keras.models import Model
from tensorflow import keras
import pickle
import pandas as pd
from User_Story_Analysis.Privacy_Dictionary.liwc_class import Liwc

dictionary = Liwc('User_Story_Analysis/Privacy_Dictionary/privacydictionary_TAWC.dic')
disclo_cnn = keras.models.load_model('User_Story_Analysis/Disclosure_CNN/cnn.h5', compile=False)
with open('User_Story_Analysis/Disclosure_CNN/transformer.pickle', 'rb') as handle:
    tokenizer = pickle.load(handle)
nlp = spacy.load("en_core_web_sm")
privacy_detector = keras.models.load_model('User_Story_Analysis/Privacy_Detector_TL/privacy_detector.h5', compile=False)


def extract_features(user_story):
    persons = ['I', 'ME', 'MY', 'MINE', 'YOU', 'YOUR', 'YOURS', 'HE', 'SHE',
               'HIS', 'HER', 'HIM', 'THEY', 'THEM', 'THEMSELVES', 'OUR', 'WE']
    location = ['LOC', 'GPE', 'ORG', 'FAC', 'CARDINAL']
    all_entities = location + ['PERSON', 'HEALTH', 'MONEY', 'DATE', 'TIME']

    doc = nlp(u'' + user_story)

    text_tokenized = []
    modified_tokens = []
    modified_tokens_dep = []
    modified_tokens_pos = []

    for t in doc:
        if str(t) not in punctuation:
            if t.ent_type_ == '':
                if t.text.upper() in persons:
                    modified_tokens.append('PERSON')
                    text_tokenized.append(t.text)
                else:
                    modified_tokens.append(t.text)
                    text_tokenized.append(t.text)
            else:
                modified_tokens.append(t.ent_type_)
                text_tokenized.append(t.text)

    for t in doc:
        if str(t) not in punctuation:
            modified_tokens_dep.append(t.dep_)
            print(str(t), 'dep', t.dep_)

    for t in doc:
        if str(t) not in punctuation:
            modified_tokens_pos.append(t.pos_)
            print(str(t), 'pos', t.pos_)

    c, keywords, words_category = dictionary.parse(user_story.lower().split(' '))
    categories_list = [list(i) for i in c.items()]
    if str(keywords) == "[]":
        keywords = "none"
        categories_list = "none"

    return modified_tokens, modified_tokens_dep, modified_tokens_pos, categories_list, keywords, text_tokenized, words_category


def prepare_input_privacy(sentence):
    max_length = 558
    output = disclo_cnn.layers[-4].output
    disclo_cnn_cutted = Model(disclo_cnn.input, output)

    disclo_cnn_cutted.trainable = False
    for layer in disclo_cnn_cutted.layers:
        layer.trainable = False
    modified_tokens, modified_tokens_dep, modified_tokens_pos, counter_list, k, k_grams, words_category = extract_features(
        sentence)

    encoded1 = tokenizer.texts_to_sequences(modified_tokens[:])
    encoded2 = tokenizer.texts_to_sequences(modified_tokens_dep[:])
    encoded3 = tokenizer.texts_to_sequences(modified_tokens_pos[:])

    encoded1_x = np.zeros((1, max_length))
    count = 0
    for i in encoded1:
        if len(i) > 0:
            encoded1_x[0, count] = i[0]
        count += 1

    encoded2_x = np.zeros((1, max_length))
    count = 0
    for i in encoded2:
        if len(i) > 0:
            encoded2_x[0, count] = i[0]
        count += 1

    encoded3_x = np.zeros((1, max_length))
    count = 0
    for i in encoded3:
        if len(i) > 0:
            encoded3_x[0, count] = i[0]
        count += 1
    encoded4_x = np.zeros((1, max_length))
    count = 0
    for i in tokenizer.texts_to_sequences(str(counter_list)):
        if len(i) > 0:
            encoded4_x[0, count] = i[0]
        count += 1
    encoded5_x = np.zeros((1, max_length))
    count = 0
    for i in tokenizer.texts_to_sequences(str(k)):
        if len(i) > 0:
            encoded5_x[0, count] = i[0]
        count += 1
    output_disclo = disclo_cnn_cutted.predict([encoded1_x, encoded2_x, encoded3_x])
    df_coeff = pd.DataFrame(
        {'word': k_grams
         })

    return encoded4_x, encoded5_x, output_disclo, df_coeff, k, words_category


def prediction(us):
    input1, input2, input3, df_coeff, keywords, words_category = prepare_input_privacy(us)

    us_prediction = privacy_detector.predict([input1, input2, input3])
    print(us_prediction.item(0))
    if us_prediction.item(0) >= 0.5:
        print("Privacy content")
    else:
        print("No privacy content")

    print("\nPrivacy words detected:")

    for word in words_category:
        print("\nPrivacy word: ")
        print(word[0])
        print("\nPrivacy category: ")
        print(word[1])
        if word[2]:
            print("\nPrivacy description: ")
            print(word[2])

    return us_prediction, words_category
