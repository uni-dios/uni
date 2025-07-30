from flask import Flask, jsonify, request
import stanza
from helpers.dbsqlite import sql
import inflect

from word2number import w2n
from datetime import datetime


from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()


nlp = stanza.Pipeline('en', processors='tokenize,pos,lemma,depparse,constituency', use_gpu=True, pos_batch_size=32, download_method=None)

app = Flask(__name__)




def retrieve_entity_count(entity_name):
    # Retrieve the count of entities with the given name.
    entity = sql("SELECT COUNT(*) as count FROM user_entities WHERE ent_name = ? AND user_id = ?", (entity_name, 1), single=True)

    if entity:
        return entity['count']
    else:
        return 0



def tree_to_json_with_all_info(tree, sentence, word_index=None):
    
    if word_index is None:
        word_index = [0]  # Use list to make it mutable
    
    if not tree.children:  # Leaf node
        # Get the corresponding word from the sentence
        if word_index[0] < len(sentence.words):
            word = sentence.words[word_index[0]]
            
            # Find the head word info (for readability)
            head_text = None
            head_lemma = None
            if word.head > 0:  # head=0 means root
                head_word = sentence.words[word.head - 1]  # head is 1-indexed
                head_text = head_word.text
                head_lemma = head_word.lemma
            
            # Get before/after word info
            before_text = None
            before_lemma = None
            after_text = None
            after_lemma = None
            
            current_idx = word_index[0]
            
            # Before word (previous word)
            if current_idx > 0:
                before_word = sentence.words[current_idx - 1]
                before_text = before_word.text
                before_lemma = before_word.lemma
            
            # After word (next word)
            if current_idx < len(sentence.words) - 1:
                after_word = sentence.words[current_idx + 1]
                after_text = after_word.text
                after_lemma = after_word.lemma
            
            result = {
                "label": tree.label,
                "text": word.text,
                "lemma": word.lemma,
                "pos": word.upos,
                "dep": word.deprel,
                "head": word.head,
                "head_text": head_text,
                "head_lemma": head_lemma,
                "before_text": before_text,
                "before_lemma": before_lemma,
                "after_text": after_text,
                "after_lemma": after_lemma
            }
            word_index[0] += 1
            return result
        else:
            return {tree.label: tree.label}
    else:
        return {
            tree.label: [tree_to_json_with_all_info(child, sentence, word_index) for child in tree.children]
        }


### INTENT MANAGEMENT FUNCTIONS ###

def get_intent_id_by_protocol(intent_protocol):
    
    # Make camel case and replace spaces with underscores for the intent name.
    intent_name = intent_protocol.replace("-", "_").lower().capitalize()

    intent = sql("SELECT * FROM intents WHERE int_protocol = ?", (intent_protocol,), single=True)

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not intent:
        int_id = sql("INSERT INTO intents (int_protocol, int_name, int_created, int_updated) VALUES (?, ?, ?, ?)", (intent_protocol, intent_name, current_time, current_time))
    else:
        int_id = intent['int_id']

    return int_id

    

def process_sentence_for_possession_intent(sentence):
    
    subject = None
    intent_verb = None
    intent = None
    quantifier = None
    quantifier_word = None
    object = None
    is_question = False
    
    constituency = sentence.constituency
    
    # print(f"\n >>> Debugging: Constituency before: \n{constituency}")

    constituency = tree_to_json_with_all_info(constituency, sentence)

    # print(f"\n >>> Debugging: Constituency after parsing: \n{constituency}")
    
    # Now we need to crawl the tree and see if we can find the "ROOT" which should also be in the first encountered VP (verb phrase) and the first encountered VBP (verb, present tense), and its lemma is 'have', or 'possess', we have encountered the intent of possession.
        
    if "ROOT" in constituency:
        root_phrase = constituency.get("ROOT", None)[0]
        
        print(f"\n >>> Debugging: Found ROOT in constituency: \n{root_phrase}")
        
        ### Checking for sentence phrases.
        if "S" in root_phrase:
            sentence_phrases = root_phrase.get("S", None)
            print(f"\n >>> Debugging: Found S (sentence) in ROOT: \n{sentence_phrases}")

            for sentence_phrase in sentence_phrases:

                print(f"\n >>> Debugging: Processing sentence phrase: \n{sentence_phrase}")

                if "NP" in sentence_phrase:
                    
                    noun_phrase = sentence_phrase.get("NP", None)[0]
                    print(f"\n >>> Debugging: Found NP in S: \n{noun_phrase}")
                    
                    if noun_phrase:
                        # Means we have a subject in the sentence.
                        # print(f"\n >>> Debugging: Found NP in S: \n{noun_phrase}")
                        # Any PRP?
                        pronoun = noun_phrase.get("PRP", None)[0] if "PRP" in noun_phrase else None
                        if pronoun:
                            subject = pronoun.get("text", None)
                            print(f"\n >>> Debugging: Found PRP in NP : \n{pronoun}")
                            # print(f"\n >>> Debugging: Found the subject of the sentence: \n{pronoun.get('text', 'Unknown')}")
                            # We can assume that the pronouns are the entities.

                if "VP" in sentence_phrase:

                    main_verb_phrases = sentence_phrase.get("VP", None)
                    
                    for main_verb_phrase in main_verb_phrases:
                        print(f"\n >>> Debugging: Found VP in constituency: \n{main_verb_phrase}")

                        if "VBP" in main_verb_phrase:

                            verb_present_tense = main_verb_phrase.get("VBP", None)[0]
                            print(f"\n >>> Debugging: Found VBP in VP: \n{verb_present_tense}")
                            
                            if verb_present_tense:
                                print(f"\n >>> Debugging: Found VBP in VP: \n{verb_present_tense}")
                                # We can assume that the verb present tense is the main verb of the sentence.
                                if verb_present_tense.get("lemma", None) in ["have", "possess"]:
                                    intent_verb = verb_present_tense['lemma']
                                    intent = "user_informs_of_possession"
                                    print(f"\n >>> Debugging: Found intent of possession with lemma: \n{verb_present_tense['lemma']}")
                                    

                        if "NP" in main_verb_phrase:

                            noun_phrases = main_verb_phrase.get("NP", None)
                            # print(f"\n >>> Debugging: Found NP in VP: \n{noun_phrase}")

                            for noun_phrase in noun_phrases:
                                # Means we have a direct object in the verb phrase.
                                # print(f"\n >>> Debugging: Found NP in VP: \n{noun_phrase}")
                                # Any CDs?
                                
                                cardinal_numbers = noun_phrase.get("CD", None)[0] if "CD" in noun_phrase else None
                                if cardinal_numbers:
                                    quantifier_word = cardinal_numbers.get("text", None)
                                    # print(f"\n >>> Debugging: Found CD in NP: \n{cardinal_numbers}")
                                    # We can assume that the cardinal numbers are the quantifiers.
                                
                                determiners = noun_phrase.get("DT", None)[0] if "DT" in noun_phrase else None
                                if determiners:
                                    determiner = determiners.get("text", None)
                                    # print(f"\n >>> Debugging: Found DT in NP: \n{determiner}")
                                    # We can assume that the determiners are the qualifiers. Convert them into numbers.
                                    if determiner.lower() in ["a", "an", "the", "this", "that", "these", "those"]:
                                        # Convert 'DT' to 1 if it matches the words above.
                                        print(f"The determiner '{determiner}' is a qualifier.")
                                        quantifier = 1 if not quantifier else quantifier
                                
                                # Any NNS?
                                found_nouns = noun_phrase.get("NNS", None)[0] if "NNS" in noun_phrase else None
                                if found_nouns:
                                    object = found_nouns.get("text", None)
                                    # print(f"\n >>> Debugging: Found NNS in NP: \n{found_nouns}")
                                    # We can assume that the plural nouns are the entities.
                                    
                                found_noun = noun_phrase.get("NN", None)[0] if "NN" in noun_phrase else None
                                if found_noun:
                                    object = found_noun.get("text", None)
                                    # print(f"\n >>> Debugging: Found NN in NP: \n{found_noun}")
                                    # We can assume that the singular nouns are the entities.
                                    
                                if object:
                                    object = lemmatizer.lemmatize(object)

        elif "SQ" in root_phrase:
            
            is_question = True

            question_phrase_parts = root_phrase.get("SQ", None)
            # print(f"\n >>> Debugging: Found SQ (sentence question) in ROOT: \n{question_phrase_parts}")

            # If we have a SQ (sentence question) in the ROOT, we can assume that the subject is the first word in the sentence.

            found_do = False
            found_pronoun = False

            for question_phrase_part in question_phrase_parts:
                # print(f"\n >>> Debugging: Processing sentence phrase in SQ: \n{question_phrase_part}")

                if "VBP" in question_phrase_part:
                    
                    # print(f"\n >>> Debugging: Found VBP in constituency: \n{question_phrase_part}")
                    
                    # Look for "do" as optional addition.
                    verb_present_tense = question_phrase_part.get("VBP", None)[0]
                    
                    # print(f"\n >>> Debugging: Found VBP in SQ: \n{verb_present_tense}")
                    
                    if verb_present_tense.get("lemma", None).lower() == "do":
                        found_do = True
                        # print(f"\n >>> Debugging: Found 'do' in VBP: \n{verb_present_tense}")

                if "NP" in question_phrase_part:
                    
                    # Look for the "I" noun for the user.
                    noun_phrase = question_phrase_part.get("NP", None)[0]
                    # print(f"\n >>> Debugging: Found NP in constituency: \n{noun_phrase}")
                    
                    if "PRP" in noun_phrase:
                        proper_noun = noun_phrase.get("PRP", None)[0]

                        if proper_noun.get("lemma", None).lower() == "i":
                            found_pronoun = True
                            subject = proper_noun.get("text", None)
                            # print(f"\n >>> Debugging: Found 'I' in NP: \n{proper_noun}")

                if "VP" in question_phrase_part:
                    
                    verb_phrase = question_phrase_part.get("VP", None)
                    # print(f"\n >>> Debugging: Found VP in constituency: \n{question_phrase_part}")
                    
                    # Loop through the children of the VP to find VB and NP with DT/CD and NNS/NN.
                    for verb_phrase_part in verb_phrase:

                        if "VB" in verb_phrase_part:
                            
                            verb_base = verb_phrase_part.get("VB", None)[0]
                            # print(f"\n >>> Debugging: Found VB in VP: \n{verb_base}")
                            
                            if verb_base.get("lemma", None) in ["have", "possess"]:
                                
                                intent_verb = verb_base['lemma']
                                # print(f"\n >>> Debugging: Found lemma for VB: \n{intent_verb}")

                                # We need to detect if we find the words "do" and pronouns like "I" in the sentence.
                                
                                if found_do and found_pronoun:
                                    intent = "user_requests_possession_availability"
                                    # print(f"\n >>> Debugging: Found intent of possession with lemma: \n{intent_verb}")

                        if "NP" in verb_phrase_part:
                            # print(f"\n >>> Debugging: Found NP in VP: \n{verb_phrase_part}")

                            noun_phrase_parts = verb_phrase_part.get("NP", None)

                            # Look for DT/CD and NNS/NN.
                            for noun_phrase_part in noun_phrase_parts:

                                determiner = noun_phrase_part.get("DT", None)
                                cardinal_number = noun_phrase_part.get("CD", None)
                                
                                object = noun_phrase_part.get("NNS", None) or noun_phrase_part.get("NN", None)
                                # singularize the object if it is a plural noun.
                                if object:
                                    object = object[0]
                                    object = lemmatizer.lemmatize(object.get("lemma", None))
                                
                                if determiner:
                                    determiner = determiner[0] 
                                    # print(f"\n >>> Debugging: Found DT/CD in NP: \n{noun_phrase_part}")
                                    
                                    determiner_word = determiner.get("text", None)
                                    if determiner_word.lower() in ["a", "an", "the", "this", "that", "these", "those"]:
                                        # Convert 'DT' to 1 if it matches the words above.
                                        print(f"The determiner '{determiner_word}' is a qualifier.")
                                        quantifier = 1 if not quantifier else quantifier
                                    
                                if cardinal_number:
                                    cardinal_number = cardinal_number[0]
                                    quantifier_word = cardinal_number.get("text", None)
                                    if quantifier_word:
                                        quantifier = w2n.word_to_num(quantifier_word)
                                    
                                
                                    

    else:
        # print(" >>> Debugging: No ROOT found in constituency.")
        return "No ROOT found in constituency."
    
    
    
    ### Completed intent detection, now we move onto entities. ###
    
    
    # Collected the parts, now process for intent, and update entities and their qualifiers and quantifiers.
    if not is_question and subject and subject.lower() == "i" and intent_verb in ["have", "possess"]:

        # Convert cardinal number into an integer even from text. What library can we use for that?
        
        if quantifier_word:
            quantifier = w2n.word_to_num(quantifier_word)
            
        print (f" >>> For the sentence: \n{sentence.text}\n...we have detected the following information:")
        print (f"Subject: {subject}, Intent Verb: {intent_verb}, Intent: {intent}, Quantifier: {quantifier}, Object: {object}")

        # Now we process the data.
        # First we check to see if we have an intent for 'user_informs_of_possession'. If not, add it.
        if intent:
            int_id = get_intent_id_by_protocol(intent)
        
        # Then, we check to see if we have any entities with the same name as the object. If not, add it and assign it to our user.
        if object and quantifier:
            entity_ids = check_existing_entity_for(object, quantifier)
            print(f" >>> Debugging: Found entity IDs: {entity_ids}")
        
        # Connect the entity to the intent for this user and this message.
        # Use the cardinal number to insert as many entities.
        
        # Check to see how many entities we have in the DB.
        entity_count = retrieve_entity_count(object)
        plural_obj = inflect.engine().plural(object)

        # If the entity count differs, correct the user.
        if entity_count != quantifier:
            
            # We can assume that the user has made a mistake in the quantifier.
            # Let's pluralize the object for the response.
            print(f" >>> Debugging: Entity count differs from quantifier. Expected {quantifier}, found {entity_count}.")
            
            if entity_count == 0 or entity_count > 1:
                return f"You mentioned you have {quantifier} {plural_obj}, but I found {entity_count} in the database. Please check your input."

            else:
                return f"You mentioned you have 1 {object}, but I found {entity_count} {plural_obj} in the database. Please check your input."
        else:
        

            if quantifier == 0 or quantifier > 1:
                # If the entity count is 0 or greater than 1, we can return a pluralized response.
                return f"Thank you for letting me know that you have {quantifier} {plural_obj}."
            else:
                
                return f"Thank you for letting me know you have 1 {object}."

    elif is_question and subject and subject.lower() == "i" and intent_verb in ["have", "possess"] and found_do:
        
        # This means that the user is asking if they have an entity of the object type.
        # print(f" >>> Debugging: Detected a question about possession with intent verb: {intent_verb} and subject: {subject}.")
        
        # pluralize for real. Don't cheat.
        plural_obj = inflect.engine().plural(object)
        
        entity_count = retrieve_entity_count(object)

        if entity_count == 0:
            
            
            return f"You do not have any {plural_obj}."
        
        elif entity_count == 1:
            
            entity_count_words = inflect.engine().number_to_words(entity_count)
            return f"You have {entity_count_words} {object}."
        
        else:
            
            entity_count_words = inflect.engine().number_to_words(entity_count)
            return f"You have {entity_count_words} {plural_obj}."

    return False


### SYNTACTIC PARSING and ENTITY MANAGEMENT ###

def check_existing_entity_for(entity_name, quantifier = 1):
    # Check if the entity already exists in the database.
    entity = sql("SELECT * FROM user_entities WHERE ent_name = ?", (entity_name,), single=True)
    
    entity_ids = []
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if not entity:
        # We can use a loop to insert the same entity multiple times.
        for _ in range(quantifier):
            # If quantifier is greater than 1, we insert multiple entities.
            # This is useful for cases like "I have 3 apples".
            # Insert the entity into the database.
            ent_id = sql("INSERT INTO user_entities (ent_name, user_id, ent_created, ent_updated) VALUES (?, ?, ?, ?)", (entity_name, 1, current_time, current_time))  # Assuming user_id is 1 for now.
            entity_ids.append(ent_id)
    else:
        entity_ids.append(entity['ent_id'])

    return entity_ids


@app.route('/process_syntactic_parsing', methods=['GET', 'POST'])
@app.route('/process_syntactic_parsing/<string:user_input>', methods=['GET', 'POST'])
def process_syntactic_parsing(user_input = "How's the weather?"):
    
    # This is the new code where we will focus on implementing syntactic parsing.
    
    # Let's gather the user message and parse it properly.

    print(f" >>> Debugging: User Input Before: {user_input}")

    if request.method == 'POST':
        # If the request is a POST, we assume the user input is in the JSON body.
        data = request.get_json()
        user_input = data.get('user_input', "How's the weather?")
    elif request.method == 'GET':
        # If the request is a GET, we assume the user input is in the URL.
        user_input = "How's the weather?"


    print(f" >>> Debugging: User Input After: {user_input}")

    
    for paragraph in user_input.split("/n"):
        
        doc = nlp(paragraph)
        print(f" >>> Debugging: Document created with {len(doc.sentences)} sentences.")
        
        for sentence in doc.sentences:
            
            print(f" >>> Debugging: Processing sentence: {sentence.text}")
            
            # Let's check for words. If there are no words in the sentence, we can skip it.
            
            if not sentence.words:
                # print(" >>> Debugging: No words found in the sentence, skipping.")
                
                return jsonify({"message": "No words found in the sentence.", "success": False}), 200
            
            # Let's see what sentence is before we process it.
            print(f" >>> Debugging: Sentence before processing: {sentence.text}")
            
            intent_response = process_sentence_for_possession_intent(sentence)
            
            print(f" >>> Debugging: Sentence before processing: {sentence.text}")
            
            if intent_response:
                # If we have a response, we can return it.
                print(f" >>> Debugging: Found intent response: {intent_response}")
                
                # We can also return the intent ID.
                intent_id = get_intent_id_by_protocol("user_informs_of_possession")

                return jsonify({"message": intent_response, "success": True, "intent_id": intent_id}), 200

    # First, we do constituency parsing to identify the structure of the sentence and extract the intent via the main verb phrase.
    
    # Then, we do dependency parsing to extract the entities, their qualifiers and quantifiers.
    
    # Work on the verb 'to have' for the intent `user_informs_of_possession`.

    return jsonify({"message": "", "success": False}), 200
    return (False, 0)

if __name__ == "__main__":
    


    app.run(debug=False, host='0.0.0.0', port=5012)