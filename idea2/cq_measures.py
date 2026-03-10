"""
Measures to evaluate the quality of generated questions using sentence embeddings.
This module provides functions to calculate sentence embeddings, cosine similarity,
cohesion, and visualize the similarity between generated and reference questions.
"""

import numpy as np
import matplotlib.pyplot as plt

from tqdm import tqdm

## -- Lazy-load both the library AND the model to make runner.py faster
_model = None
_sentence_transformers = None

def get_sentence_transformers():
    """Lazy-loads the sentence_transformers module to avoid loading PyTorch at import time."""
    global _sentence_transformers
    if _sentence_transformers is None:
        from sentence_transformers import SentenceTransformer, util as st_util
        _sentence_transformers = {'SentenceTransformer': SentenceTransformer, 'util': st_util}
    return _sentence_transformers

def get_model():
    """Lazy-loads the SentenceTransformer model. It is not needed only on import, but only
    when embeddings are needed which is not during the first iteration of the script.
    
    Returns
        SentenceTransformer: An instance of the SentenceTransformer model.

    """
    global _model
    if _model is None:
        st = get_sentence_transformers()
        _model = st['SentenceTransformer']('all-mpnet-base-v2')
    return _model

def calculate_embeddings(questions):
  """Calculates sentence embeddings for a list of questions.

  Parameters
  ----------
  questions : list of str
      The list of questions to calculate embeddings for.

  Returns
  -------
  numpy.ndarray
      A NumPy array containing the sentence embeddings.
  """
  model = get_model()
  return model.encode(questions, convert_to_tensor=True).cpu().numpy()


def calculate_similarity_matrix(generated_embeddings, reference_embeddings):
  """Calculates the cosine similarity matrix between two sets of embeddings.

  Parameters
  ----------
  generated_embeddings : numpy.ndarray
      A NumPy array containing the embeddings of generated questions.
  reference_embeddings : numpy.ndarray
      A NumPy array containing the embeddings of reference questions.

  Returns
  -------
  numpy.ndarray
      A NumPy array containing the cosine similarity matrix.
  """
  st = get_sentence_transformers()
  cosine_similarities = st['util'].cos_sim(generated_embeddings, reference_embeddings)
  return cosine_similarities.cpu().numpy()


def calculate_cohesion(similarity_matrix):
  """Calculates the average similarity from a similarity matrix.

  Parameters
  ----------
  similarity_matrix : numpy.ndarray
      A NumPy array containing the cosine similarity matrix.

  Returns
  -------
  float
      The average similarity score.
  """
  return np.mean(similarity_matrix)


def find_best_matches(similarity_matrix, generated_questions, reference_questions):
  """Finds the best matching reference question for each generated question.

  Parameters
  ----------
  similarity_matrix : numpy.ndarray
      A NumPy array containing the cosine similarity matrix.
  generated_questions : list of str
      The list of generated questions.
  reference_questions : list of str
      The list of reference questions.

  Returns
  -------
  list of tuple
      A list of tuples, each containing a generated question and its 
      best matching reference question.
  """
  best_matches = []
  for i, generated_question in enumerate(generated_questions):
    best_match_index = np.argmax(similarity_matrix[i])
    best_matches.append((generated_question, reference_questions[best_match_index]))
  return best_matches

def remove_similar_generated(similarity_matrix, generated_questions, threshold) -> list:
    """
    Removes generated questions that are too similar to each other based on a threshold.

    Args:
        similarity_matrix (numpy.ndarray): The cosine similarity matrix of generated questions.
        generated_questions (List[str]): The list of generated questions.
        threshold (float): The similarity threshold above which questions will be removed.

    Returns:
        list: A list of generated questions that are not too similar to each other.

    """

    to_remove = set()
    for i in range(similarity_matrix.shape[0]):
        for j in range(similarity_matrix.shape[1]):
            if i != j and similarity_matrix[i, j] > threshold:
                to_remove.add(i)

    print(f"Removing {len(to_remove)} questions that are too similar to each other (threshold: {threshold})")
    return [q for idx, q in tqdm(enumerate(generated_questions)) if idx not in to_remove]

def run_simple_similarity_analysis(cqs, selfcheck=True):
   """Runs a simple similarity analysis on the generated competency questions.

   This function calculates embeddings for the generated questions, computes a similarity matrix,
   and then analyzes the cohesion and similarity of the questions.

   Parameters
   ----------
   cqs : list of str
       The list of generated competency questions.

   selfcheck : bool
       Whether to perform the embeddings against themselves (see if two cqs in a set are too similar)

    Returns
    -------
    list of str
        A list of filtered generated questions.

   """
   
   generated_embeddings = calculate_embeddings(cqs)
   similarity_matrix = calculate_similarity_matrix(generated_embeddings, generated_embeddings)

   print(f"\nCohesion of generated CQs: {calculate_cohesion(similarity_matrix)}")

   filter_similar = remove_similar_generated(similarity_matrix, cqs, threshold=0.95)

   return filter_similar



def visualize_cohesion(similarity_matrix, generated_questions, reference_questions):
  """Visualizes the cohesion between two sets of questions using a heatmap.

  Parameters
  ----------
  similarity_matrix : numpy.ndarray
      A NumPy array containing the cosine similarity matrix.
  generated_questions : list of str
      The list of generated questions.
  reference_questions : list of str
      The list of reference questions.
  """
  fig, ax = plt.subplots()
  im = ax.imshow(similarity_matrix, cmap='viridis')

  ax.set_xticks(np.arange(len(reference_questions)))
  ax.set_yticks(np.arange(len(generated_questions)))
  ax.set_xticklabels(reference_questions, rotation=45, ha="right")
  ax.set_yticklabels(generated_questions)

  cbar = ax.figure.colorbar(im, ax=ax)
  cbar.ax.set_ylabel("Cosine Similarity", rotation=-90, va="bottom")

  for i in range(len(generated_questions)):
    for j in range(len(reference_questions)):
      text = ax.text(j, i, f"{similarity_matrix[i, j]:.2f}",
                     ha="center", va="center", color="w")

  ax.set_title("Question Similarity Heatmap")
  fig.tight_layout()
  plt.show()
