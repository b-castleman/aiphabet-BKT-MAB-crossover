## Imports
from pyBKT.models import *
import numpy as np
import pandas as pd
import numpy as np
import json
import time
import pickle
import math
import copy
from tree import Static_Tree
import random
from ZPDES_Memory import ZPDES_Memory


if __name__ == '__main__':

    print("Import Complete")

    ## Setup - BKT
    # model = Model(seed = 42)
    # df = pd.read_csv('aiphabet_pseudo_student_data.csv')
    defaults={'order_id': 'row',
                    'skill_name': 'skill_name',
                    'correct': 'correct',
                    'user_id': 'student_id',
                    'multilearn': 'Problem Name',
                    'multiprior': 'correct',
                    'multipair': 'Problem Name',
                    'multigs': 'Problem Name',
                    'folds': 'student_id'}


    # Define the simulation inputs
    #tree_name = "./trees/applications_of_ai_tree.txt"
    #skills = ['ai_definitions','thinking_rationally','acting_rationally','thinking_humanlike','acting_humanlike']
    #tree_name = "./trees/turing_test_tree.txt"
    # tree_name = './trees/applications_of_ai_tree.txt'
    #skills = ['applications_of_ai_examples']
    #tree_name = './trees/history_of_ai_tree.txt'
    #skills = ['gestation_era','early_enthusiasm_era','knowledge_based_era','ai_becomes_scientific']
    # tree_name = './trees/rational_agents_tree.txt'
    # skills = ['acting_rationally','peas','environment_types']
    tree_name = './trees/search_tree.txt'
    skills = ['search_definition','simple_search','constraint_search','adversarial_search']
    # tree_name = './trees/logical_agents_tree.txt'
    # skills = ['wumpus_world','wumpus_inference_examples','logic_review','knowledge_base_definition']
    #skills = ['turing_test_definition','turing_test_examples']
    #['applications_of_ai_examples']
    #['gestation_era','early_enthusiasm_era','knowledge_based_era','ai_becomes_scientific']
    #['wumpus_world','wumpus_inference_examples','logic_review','knowledge_base_definition']
    #['acting_rationally','peas','environment_types']
    #['search_definition','simple_search','constraint_search','adversarial_search']
    #

    # model.fit(data = df, defaults = defaults, skills = skills)
    with open("pickled_model.pkl", 'rb') as f:
        model =  pickle.load(f)  # deserialize using load()
    print(model)
    print("Fitting Complete.")

    roster = Roster(students = ['Student_A','Student_B','Student_C','Student_D','Student_E','Student_F'], skills = skills, model = model)

    print("Roster Complete.")


    ## Setup - ZPDES
    # Get tree
    tree_fn = tree_name
    progression_tree = Static_Tree(tree_filename=tree_fn)


    # Set parameters
    params = {
        'history_length': 2,
        'progress_threshold': 0.74,
        'memory_threshold': math.exp(-12),
        'memory_multiplier': 10e10
    }

    # Iterate for all ZPDES students
    for student_num in ['A', 'B', 'C']:
        # Instantiate progression algorithm object
        progression_algorithm = ZPDES_Memory(progression_tree, params=params)
        problem_give = progression_algorithm.get_current_problem()

        print("Setup Complete.")

        ## Iterate through the problem recommendation cycle for Student_A - Student_C
        while problem_give != None:
            # Get the concept and problem number
            splitProblem = problem_give.split("_p")
            problemNumber = int(splitProblem[-1]) - 1
            conceptName = "_p".join(splitProblem[:-1])

            # Probability we've mastered the concept
            P_mastered = roster.get_mastery_prob(conceptName, 'Student_' + student_num)
            mastery_on_question = random.choices([True,False], weights=[P_mastered,1-P_mastered])

            # Get correctness
            if mastery_on_question:
                # Probability of slip?
                Correctness_of_Student_Answer = True
                P_slips = model.coef_[conceptName]['slips']

                if random.random() < P_slips:
                    Correctness_of_Student_Answer = False

            else:
                # Probability of guess?
                Correctness_of_Student_Answer = False
                P_guesses = model.coef_[conceptName]['guesses']

                if random.random() < P_guesses:
                    Correctness_of_Student_Answer = True

            # Inform correctness to the ZPDES algorithm
            progression_algorithm.student_answer_update(Correctness_of_Student_Answer)

            # Inform correctness to the BKT algorithm
            roster.update_state(conceptName, 'Student_' + student_num, int(Correctness_of_Student_Answer))

            # Get next problem
            problem_give = progression_algorithm.get_current_problem()

        print("Student_" + student_num +  "(ZPDES) Complete.")

    ## Iterate through the static problem cycle for Student_D - Student_F
    for student_num in ['D','E','F']:
        for skill in skills:
            for problem_num in range(2):
                conceptName = skill

                # Probability we've mastered the concept
                P_mastered = roster.get_mastery_prob(conceptName, 'Student_' + student_num)
                mastery_on_question = random.choices([True, False], weights=[P_mastered, 1 - P_mastered])

                # Get correctness
                if mastery_on_question:
                    # Probability of slip?
                    Correctness_of_Student_Answer = True
                    P_slips = model.coef_[conceptName]['slips']

                    if random.random() < P_slips:
                        Correctness_of_Student_Answer = False

                else:
                    # Probability of guess?
                    Correctness_of_Student_Answer = False
                    P_guesses = model.coef_[conceptName]['guesses']

                    if random.random() < P_guesses:
                        Correctness_of_Student_Answer = True

                # Inform correctness to the BKT algorithm
                roster.update_state(conceptName, 'Student_' + student_num, int(Correctness_of_Student_Answer))

        print("Student_" + student_num + " (Static) Complete.\n")

    # Print statistics
    for skill in skills:
        for student_num in ['A','B','C','D','E','F']:
            print("\nSkill:",skill)
            print("Student_" + student_num + "'s probability of mastery (t = t_f):", roster.get_mastery_prob(skill, 'Student_' + student_num))













    # # He should remain unmastered.
    # print("Bob's mastery (t = 2):", roster.get_state_type('Calculate unit rate', 'Bob'))
    # print("Bob's probability of mastery (t = 2):", roster.get_mastery_prob('Calculate unit rate', 'Bob'))
    # #model.fit(data_path = 'as.csv', forgets = True, skills = 'Box and Whisker')
    # # {'Box and Whisker': {'prior': 0.6041037401184252,
    #   # 'learns': array([0.29935353]),
    #   # 'guesses': array([0.33519941]),
    #   # 'slips': array([0.09650188]),
    #   # 'forgets': array([0.06483686])}}
    # model.coef_
