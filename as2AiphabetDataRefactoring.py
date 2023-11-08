import pandas as pd
import json

fn_assessments = 'as.csv'
fn_aiphabet_problems = '/Users/blake/Documents/AIED Research/MAB/Automatic_Curriculum_ZPDES_Memory/problems/problems.json'

df_old = pd.read_csv(fn_assessments,nrows=99999)
df_new = pd.DataFrame(columns=['row','skill_name','student_id','correct','Problem Name'])

# old dataframe col to new dataframe col
col_mapping = {'order_id': 'row',
                'skill_name': 'skill_name',
                'correct': 'correct',
                'user_id': 'student_id',
                'template_id': 'Problem Name',
                'multiprior': 'correct',
                'template_id': 'Problem Name',
                'template_id': 'Problem Name',
                'user_id': 'student_id'}

# Opening Problems JSON file
with open(fn_aiphabet_problems) as json_file:
    aiphabet_problems = json.load(json_file)

# Hashmap of assessments problems to aiphabet problems
hm_concept_mapping = dict()
used_new_concepts = set()
hm_problem_mapping = dict()
used_new_problems = set()

for index, row in df_old.iterrows():
    concept_old = row['skill_name']
    problem_old = row['template_id']

    # Set the concept
    if concept_old in hm_concept_mapping:
        concept_new = hm_concept_mapping[concept_old]
    else:
        concept_new = None
        # Find a concept that hasn't been taken
        for potential_new_concept in aiphabet_problems:
            if potential_new_concept not in used_new_concepts:
                # Set the concept path
                concept_new = potential_new_concept
                hm_concept_mapping[concept_old] = concept_new
                used_new_concepts.add(concept_new)
                break

        # Have all concepts been taken already?
        if concept_new == None:
            continue


    # Set the problem
    if problem_old in hm_problem_mapping:
        problem_new = hm_problem_mapping[problem_old]
    else:
        problem_new = None
        i = 1
        # Find a problem that hasn't been taken
        for potential_new_problem in aiphabet_problems[concept_new]:
            potential_new_problem = concept_new + '_p' + str(i)
            if potential_new_problem not in used_new_problems:
                # Set the problem path
                problem_new = potential_new_problem
                hm_problem_mapping[problem_old] = problem_new
                used_new_problems.add(problem_new)
                break
            i+=1

        # Have all problems been taken already?
        if problem_new == None:
            continue

    # Add this entry to the dataframae

    # {'order_id': 'row',
    #  'skill_name': 'skill_name',
    #  'correct': 'correct',
    #  'user_id': 'student_id',
    #  'template_id': 'Problem Name',
    #  'multiprior': 'correct',
    #  'template_id': 'Problem Name',
    #  'template_id': 'Problem Name',
    #  'user_id': 'student_id'}

    new_row = {'row': row['order_id'],
               'skill_name': concept_new,
               'correct':row['correct'],
               'student_id':row['user_id'],
               'Problem Name': problem_new
               }
    df_new.loc[len(df_new)] = new_row







    #print(row['order_id'], row['skill_name'])

df_new.to_csv('aiphabet_pseudo_student_data.csv', encoding='utf-8', index=False)