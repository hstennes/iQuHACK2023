from joblib import dump, load
from kernel import *
from train import extract_features
import nltk
from nltk.probability import DictionaryProbDist

opt_params = load('trained_params2.joblib')
model = load('trained_model2.joblib')
vectorizer = load('trained_vectorizer2.joblib')
encoder = load('trained_encoder2.joblib')
word_list = load('trained_wordlist2.joblib')

kernel_input = lambda x1, x2: kernel(x1, x2, opt_params)
#model.kernel = lambda x1, x2: qml.kernels.kernel_matrix(x1, x2, kernel_input)
model.kernel = "rbf"

def get_sentiment(data):
    test_data = []
    for phrase in data:
        words = phrase.split()
        test_data.append(((words, word_list), True))
    test_data = nltk.classify.apply_features(extract_features, test_data)
    test_data2 = []
    for d in test_data:
        test_data2.append(d[0])
    test_data = test_data2
    test_data = vectorizer.transform(test_data)
    result = model.predict(test_data)
    # normalize output to be from -1 to 1 instead of 0 to 1
    for i in range(len(result)):
        if result[i] == 0:
            result[i] = -1
    return result
        
