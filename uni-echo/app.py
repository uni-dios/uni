from groq import Groq
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, json
from helpers.dbsqlite import sql
from datetime import datetime

import re
import random

import stanza
from word2number import w2n
import inflect
import os
import sys
import importlib

from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()


load_dotenv()

client = Groq()

app = Flask(__name__)

nlp = stanza.Pipeline('en', processors='tokenize,pos,lemma,depparse,constituency', use_gpu=True, pos_batch_size=32, download_method=None)


@app.route('/', methods=['GET'])
def chat():
    
    messages = sql("SELECT * FROM messages WHERE sum_id = 0 ORDER BY msg_id ASC")
    
    summaries = sql("SELECT * FROM summaries ORDER BY sum_id DESC")
    
    return render_template('index.html', messages=messages, summaries=summaries)


def send_chat_with_llm(user_input):
    
    summaries = sql("SELECT * FROM summaries ORDER BY sum_id DESC")
    
    messages = []
    messages.append({
        "role": "system",
        "content": f"The following is a collection of summaries from previous conversations. Use them to inform your responses."
    })
    
    # Each summary is added to the messages list. This allows the LLM to have context from previous summaries.
    for summary in summaries:
        messages.append({
            "role": "system",
            "content": f"Title: {summary['sum_title']}\nSummary: {summary['sum_content']}\nDate: {summary['sum_created']}"
        })
    
    messages.append({
        "role": "system",
        "content": f"The summaries have completed. The following is your current conversation history. Use it to inform your responses."
    })
    
    db_messages = sql("SELECT * FROM messages WHERE sum_id = 0 ORDER BY msg_id ASC")
    
    first_message = db_messages[0] if db_messages else None
    if first_message:
        messages.append({
            "role": "system",
            "content": f"The first message in this conversation was sent on { first_message['msg_created'] }. That is when this current conversation started."
        })
    
    for msg in db_messages:
        if msg['msg_role'] == 'user':
            messages.append({
                "role": "user", 
                "content": msg['msg_content']
            })
        elif msg['msg_role'] == 'assistant':
            messages.append({
                "role": "assistant", 
                "content": msg['msg_content']
            })
            
    # Add the new user input to the messages list.
    messages.append({
        "role": "user",
        "content": user_input
    })
    
    # Call our API:
    chat_completion = client.chat.completions.create(
        messages=messages,
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        temperature=0.1,
    )

    response = chat_completion.choices[0].message.content
    return response


def get_intent_id_by_protocol(intent_protocol):
    
    # Make camel case and replace spaces with underscores for the intent name.
    intent_name = intent_protocol.replace("-", "_").lower().capitalize()
    
    intent = sql("SELECT * FROM intents WHERE int_protocol = ?", (intent_protocol,), single=True)
    
    if not intent:
        int_id = sql("INSERT INTO intents(int_protocol, int_name) VALUES (?, ?)", (intent_protocol, intent_name, ))
    else:
        int_id = intent['int_id']
    
    return int_id


def get_intent_protocol_by_id(int_id):
    
    intent = sql("SELECT * FROM intents WHERE int_id = ?", (int_id,), single=True)
    
    return intent['int_protocol']


def user_requests_current_time(prev_answer = None):

    current_time = datetime.now().strftime("%I:%M %p")
    
    if prev_answer == current_time:
        # If the previous answer is the same as the current time, we can return a simple response.
        responses = [
            f"The time is still {current_time}.",
            f"It hasn't changed, it's still {current_time}.",
            f"The time remains unchanged at {current_time}.",
            f"It's still {current_time} as before.",
            f"No change in time, it's still {current_time}.",
        ]
    else:
        # Let's come up with different responses using human language.
        responses = [
            f"The current time is {current_time}.",
            f"Right now, it is {current_time}.",
            f"Currently, the time is {current_time}.",
            f"It is now {current_time}.",
            f"The time at the moment is {current_time}.",
        ]

    return f"{random.choice(responses)}", current_time


def user_requests_current_day(prev_answer=None):

    current_day = datetime.now().strftime("%A")

    if prev_answer == current_day:
        # If the previous answer is the same as the current day, we can return a simple response.
        responses = [
            f"Today is still {current_day}.",
            f"It hasn't changed, it's still {current_day}.",
            f"The day remains unchanged at {current_day}.",
            f"It's still {current_day} as before.",
            f"It's still {current_day} as before.",
            f"No change in day, it's still {current_day}.",
        ]
    else:
        # Let's come up with different responses using human language.
        responses = [
            f"Today is {current_day}.",
            f"Right now, it is {current_day}.",
            f"Currently, it is {current_day}.",
            f"It is now {current_day}.",
            f"The day today is {current_day}.",
        ]

    return f"{random.choice(responses)}", current_day


def user_requests_current_date(prev_answer=None):

    current_date = datetime.now().strftime("%B %d, %Y")

    if prev_answer == current_date:
        # If the previous answer is the same as the current date, we can return a simple response.
        responses = [
            f"Today's date is still {current_date}.",
            f"It hasn't changed, it's still {current_date}.",
            f"The date remains unchanged at {current_date}.",
            f"It's still {current_date} as before.",
            f"No change in date, it's still {current_date}.",
        ]
    else:
        responses = [
            f"Today's date is {current_date}.",
            f"Right now, it is {current_date}.",
            f"Currently, it is {current_date}.",
            f"It is now {current_date}.",
            f"The date today is {current_date}.",
        ]
        
    return f"{random.choice(responses)}", current_date


def user_requests_repetition():
    
    current_time = datetime.now().strftime("%I:%M %p")
    # We gather the last intent from the messages.
    last_intent_record = sql("SELECT * FROM messages WHERE sum_id = 0 AND msg_role = 'user' AND int_id != 0 ORDER BY msg_id DESC", single=True)
    print(f"Last Record ID: {last_intent_record['msg_id']}" if last_intent_record else "No last record found.")

    print(f"Last Intent Record: {last_intent_record}" if last_intent_record else "No last intent record found.")

    metadata = json.loads(last_intent_record['msg_metadata']) if last_intent_record and last_intent_record['msg_metadata'] else {}

    intent_protocol = metadata.get('int_protocol', None)
    intent_id = metadata.get('int_id', 0)
    answer = metadata.get('answer', None)
    
    # Call the protocol function if it exists.
    if intent_protocol:
        intent_function = globals().get(intent_protocol, None)
        if callable(intent_function):
            response = intent_function(answer)
            return (response, answer), intent_id

        else:
            return ("I don't know how to do that.", "unknown"), False

    else:
        return ("Sorry, I don't understand what you mean by that.", "unknown"), False


def process_regex_commands(user_input):

    # This is where we would implement the RegEx command processing logic.

    detected_intent_id = 0
    
    regex_patterns = sql("SELECT * FROM regex_patterns")

    for pattern in regex_patterns:
        # Check if the user input matches the pattern.
        pattern_text = pattern['pat_regex']

        print(f" >>> Debugging: Regex Pattern: {pattern_text}")
        print(f" >>> Debugging: User Input: {user_input}")

        match = re.search(pattern_text, user_input, re.IGNORECASE)

        print(f" >>> Debugging: match: {match}")

        if not match:
            continue

        groups = match.groups() if match.groups() else []
        print(f" >>> Debugging: Groups from match: {groups}")

        # Get the intent ID for the matched pattern.
        detected_intent_id = pattern['int_id']
        print(f" >>> Debugging: Detected Intent ID: {detected_intent_id}")
        
        if detected_intent_id == 0:
            # This is where our `again` protocol comes into play.
            # Just call the again protocol.
            print(" >>> Debugging: Detected intent ID is 0, calling user_requests_repetition.")
            return user_requests_repetition()

        # Get the intent protocol by ID.
        intent_protocol = get_intent_protocol_by_id(detected_intent_id)
        print(f" >>> Debugging: Intent Protocol: {intent_protocol}")

        if not intent_protocol:
            continue
        
        # Let's find out if our function has been loaded yet.
        intent_function = globals().get(intent_protocol, None)

        if callable(intent_function):
            print(f" >>> Debugging: Found intent function '{intent_protocol}' in static regex_protocols module.")

            from inspect import signature
            sig = signature(intent_function)
            num_params = len(sig.parameters)
            print(f" >>> Debugging: Number of parameters in intent function: {num_params}")

            groups = match.groups()
            print(f" >>> Debugging: Groups from match: {groups}")

            if num_params == 0:
                response = intent_function()
                print(f" >>> Debugging: Response from Intent Function with no parameters: {response}")
            elif num_params == len(groups):
                response = intent_function(*groups)
                print(f" >>> Debugging: Calling intent function with parameters: {groups}")
            else:
                print(f" >>> Debugging: Number of parameters does not match, calling intent function with no parameters.")
                response = intent_function()
            
            print(f" >>> Debugging: Response from Intent Function: {response}")
            return (response, response), detected_intent_id
        
        # If the intent protocol is already loaded, we can directly call it.
        module_name = f"protocols.{intent_protocol}"
        mpodule_path = f"protocols/{intent_protocol}.py"

        if os.path.exists(mpodule_path):
            try:
                if module_name in sys.modules:
                    protocol_module = importlib.reload(sys.modules[module_name])
                else:
                    protocol_module = importlib.import_module(module_name)
                print(f" >>> Debugging: Protocol Module Loaded: {protocol_module}")

                intent_function = getattr(protocol_module, intent_protocol, None)

                if callable(intent_function):
                    print(f" >>> Debugging: Found intent function '{intent_protocol}' in dynamic protocol module.")
                    
                    from inspect import signature
                    sig = signature(intent_function)
                    num_params = len(sig.parameters)
                    print(f" >>> Debugging: Number of parameters in intent function: {num_params}")

                    if num_params == 0:
                        response = intent_function()
                        print(f" >>> Debugging: Response from Intent Function with no parameters: {response}")
                    elif num_params == len(match.groups()):
                        response = intent_function(*match.groups())
                        print(f" >>> Debugging: Calling intent function with parameters: {match.groups()}")
                    else:
                        print(f" >>> Debugging: Number of parameters does not match, calling intent function with no parameters.")
                        response = intent_function()

                    print(f" >>> Debugging: Response from Intent Function: {response}")
                    return (response, response), detected_intent_id

            except Exception as e:
            
                print(f" >>> Debugging: Error importing protocol module '{module_name}': {e}")
                return (False, False), False

        else:
            
            # Now, we dynamically get the intent function from the protocol module.
            # Remember, the protocol module should have a function named as the intent protocol.
        
            print(" >>> Debugging: Intent function is not callable or does not exist.")
            return (False, False), False

    return (False, False), False
    
    
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


def check_existing_entity_for(entity_name, quantifier = 1):
    # Check if the entity already exists in the database.
    entity = sql("SELECT * FROM user_entities WHERE ent_name = ?", (entity_name,), single=True)

    entity_ids = []

    if not entity:
        # We can use a loop to insert the same entity multiple times.
        for _ in range(quantifier):
            # If quantifier is greater than 1, we insert multiple entities.
            # This is useful for cases like "I have 3 apples".
            # Insert the entity into the database.
            ent_id = sql("INSERT INTO user_entities (ent_name, user_id) VALUES (?, ?)", (entity_name, 1, ))  # Assuming user_id is 1 for now.
            entity_ids.append(ent_id)
    
    else:
        entity_ids.append(entity['ent_id'])
    
    return entity_ids


def retrieve_entity_count(entity_name):
    # Retrieve the count of entities with the given name.
    entity = sql("SELECT COUNT(*) as count FROM user_entities WHERE ent_name = ? AND user_id = ?", (entity_name, 1), single=True)

    if entity:
        return entity['count']
    else:
        return 0


def process_sentence_for_possession_intent(sentence):
    
    subject = None
    intent_verb = None
    intent = None
    quantifier = None
    quantifier_word = None
    object = None
    is_question = False

    constituency = sentence.constituency

    constituency = tree_to_json_with_all_info(constituency, sentence)

    print(f"\n >>> Debugging: Constituency after parsing: \n{constituency}")

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
                    # print(f"\n >>> Debugging: Found NP in S: \n{noun_phrase}")

                    if noun_phrase:
                        # Means we have a subject in the sentence.
                        print(f"\n >>> Debugging: Found NP in S: \n{noun_phrase}")
                        # Any PRP?
                        pronoun = noun_phrase.get("PRP", None)[0] if "PRP" in noun_phrase else None

                        if pronoun:
                            subject = pronoun.get("text", None)
                            print(f"\n >>> Debugging: Found PRP in NP : \n{pronoun}")
                            print(f"\n >>> Debugging: Found the subject of the sentence: \n{pronoun.get('text', 'Unknown')}")
                            # We can assume that the pronouns are the entities.

                if "VP" in sentence_phrase:

                    main_verb_phrases = sentence_phrase.get("VP", None)

                    for main_verb_phrase in main_verb_phrases:
                        print(f"\n >>> Debugging: Found VP in constituency: \n{main_verb_phrase}")

                        if "VBP" in main_verb_phrase:

                            verb_present_tense = main_verb_phrase.get("VBP", None)[0]
                            # print(f"\n >>> Debugging: Found VBP in VP: \n{verb_present_tense}")

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
                                print(f"\n >>> Debugging: Found NP in VP: \n{noun_phrase}")
                                # Any CDs?

                                cardinal_numbers = noun_phrase.get("CD", None)[0] if "CD" in noun_phrase else None
                                if cardinal_numbers:
                                    quantifier_word = cardinal_numbers.get("text", None)
                                    print(f"\n >>> Debugging: Found CD in NP: \n{cardinal_numbers}")
                                    # We can assume that the cardinal numbers are the quantifiers.

                                determiners = noun_phrase.get("DT", None)[0] if "DT" in noun_phrase else None
                                if determiners:
                                    determiner = determiners.get("text", None)
                                    print(f"\n >>> Debugging: Found DT in NP: \n{determiner}")
                                    # We can assume that the determiners are the qualifiers. Convert them into numbers.
                                    if determiner.lower() in ["a", "an", "the", "this", "that", "these", "those"]:
                                        # Convert 'DT' to 1 if it matches the words above.
                                        print(f"The determiner '{determiner}' is a qualifier.")
                                        quantifier = 1 if not quantifier else quantifier

                                # Any NNS?
                                found_nouns = noun_phrase.get("NNS", None)[0] if "NNS" in noun_phrase else None
                                if found_nouns:
                                    object = found_nouns.get("text", None)
                                    print(f"\n >>> Debugging: Found NNS in NP: \n{found_nouns}")
                                    # We can assume that the plural nouns are the entities.

                                found_noun = noun_phrase.get("NN", None)[0] if "NN" in noun_phrase else None
                                if found_noun:
                                    object = found_noun.get("text", None)
                                    print(f"\n >>> Debugging: Found NN in NP: \n{found_noun}")
                                    # We can assume that the singular nouns are the entities.

                                if object:
                                    object = lemmatizer.lemmatize(object)

        elif "SQ" in root_phrase:

            is_question = True

            question_phrase_parts = root_phrase.get("SQ", None)
            print(f"\n >>> Debugging: Found SQ (sentence question) in ROOT: \n{question_phrase_parts}")

            # If we have a SQ (sentence question) in the ROOT, we can assume that the subject is the first word in the sentence.

            found_do = False
            found_pronoun = False

            for question_phrase_part in question_phrase_parts:
                print(f"\n >>> Debugging: Processing sentence phrase in SQ: \n{question_phrase_part}")

                if "VBP" in question_phrase_part:
                    
                    print(f"\n >>> Debugging: Found VBP in constituency: \n{question_phrase_part}")

                    # Look for "do" as optional addition.
                    verb_present_tense = question_phrase_part.get("VBP", None)[0]

                    print(f"\n >>> Debugging: Found VBP in SQ: \n{verb_present_tense}")

                    if verb_present_tense.get("lemma", None).lower() == "do":
                        found_do = True
                        print(f"\n >>> Debugging: Found 'do' in VBP: \n{verb_present_tense}")

                if "NP" in question_phrase_part:
                    
                    # Look for the "I" noun for the user.
                    noun_phrase = question_phrase_part.get("NP", None)[0]
                    print(f"\n >>> Debugging: Found NP in constituency: \n{noun_phrase}")

                    if "PRP" in noun_phrase:
                        proper_noun = noun_phrase.get("PRP", None)[0]

                        if proper_noun.get("lemma", None).lower() == "i":
                            found_pronoun = True
                            subject = proper_noun.get("text", None)
                            print(f"\n >>> Debugging: Found 'I' in NP: \n{proper_noun}")

                if "VP" in question_phrase_part:
                    
                    verb_phrase = question_phrase_part.get("VP", None)
                    print(f"\n >>> Debugging: Found VP in constituency: \n{question_phrase_part}")

                    # Loop through the children of the VP to find VB and NP with DT/CD and NNS/NN.
                    for verb_phrase_part in verb_phrase:

                        if "VB" in verb_phrase_part:
                            
                            verb_base = verb_phrase_part.get("VB", None)[0]
                            print(f"\n >>> Debugging: Found VB in VP: \n{verb_base}")

                            if verb_base.get("lemma", None) in ["have", "possess"]:
                                
                                intent_verb = verb_base['lemma']
                                print(f"\n >>> Debugging: Found lemma for VB: \n{intent_verb}")

                                # We need to detect if we find the words "do" and pronouns like "I" in the sentence.
                                
                                if found_do and found_pronoun:
                                    intent = "user_requests_possession_availability"
                                    print(f"\n >>> Debugging: Found intent of possession with lemma: \n{intent_verb}")

                        if "NP" in verb_phrase_part:
                            print(f"\n >>> Debugging: Found NP in VP: \n{verb_phrase_part}")

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
                                    print(f"\n >>> Debugging: Found DT/CD in NP: \n{noun_phrase_part}")
                                    
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
        print(" >>> Debugging: No ROOT found in constituency.")
        return "No ROOT found in constituency."

    ### Completed intent detection, now we move onto entities. ###

    # Collected the parts, now process for intent, and update entities and their qualifiers and quantifiers.
    if not is_question and subject and subject.lower() == "i" and intent_verb in ["have", "possess"]:

        # Convert cardinal number into an integer even from text. What library can we use for that?
        
        if quantifier_word:
            quantifier = w2n.word_to_num(quantifier_word)
            
        # Have to test the quantifier and object. If none, we're not talkind about possessions.
        if quantifier is None or object is None:
            return False

        print (f" >>> For the sentence: \n{sentence.text}\n...we have detected the following information:")
        print (f"Subject: {subject}, Intent Verb: {intent_verb}, Intent: {intent}, Quantifier: {quantifier}, Object: {object}")

        # Now we process the data.
        # First we check to see if we have an intent for 'user_informs_of_possession'. If not, add it.
        if intent:
            int_id = get_intent_id_by_protocol(intent)

        # Connect the entity to the intent for this user and this message.
        # Use the cardinal number to insert as many entities.
        
        # check to see if we have an existing entity count with the name.
        existing_objects = sql("SELECT * FROM user_entities WHERE ent_name = ? AND user_id = ?", (object, 1))
        existing_quantifier = len(existing_objects)
        existing_object = object
            
        # Then, we check to see if we have any entities with the same name as the object. If not, add it and assign it to our user.
        if object and quantifier:
            entity_ids = check_existing_entity_for(object, quantifier)
            print(f" >>> Debugging: Found entity IDs: {entity_ids}")

        # Pluralize the object if necessary.
        if quantifier > 1 or quantifier == 0:
            object = inflect.engine().plural(object)
        
        # Pluralize the existing_object if necessary.
        if existing_quantifier > 1 or existing_quantifier == 0:
            existing_object = inflect.engine().plural(existing_object)
        
        # Now we can return a response based on the quantifier and object.
        if quantifier != existing_quantifier and existing_quantifier != 0:
            return f"You previously mentioned you have {existing_quantifier} {existing_object}. Now you say you have {quantifier} {object}. Please clarify if this is correct."
        
        else:
            return f"Thanks for letting me know that you have {quantifier_word if quantifier_word else quantifier} {object if object else 'an entity'}."

    elif is_question and subject and subject.lower() == "i" and intent_verb in ["have", "possess"] and found_do:
        
        # This means that the user is asking if they have an entity of the object type.
        print(f" >>> Debugging: Detected a question about possession with intent verb: {intent_verb} and subject: {subject}.")

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


def process_syntactic_parsing(user_input):
    
    # This is the new code where we will focus on implementing syntactic parsing.
    
    # Let's gather the user message and parse it properly.
    
    for paragraph in user_input.split("/n"):
        
        doc = nlp(paragraph)

        for sentence in doc.sentences:
            
            print(f" >>> Debugging: Processing sentence: {sentence.text}")
            
            # Let's check for words. If there are no words in the sentence, we can skip it.
            
            if not sentence.words:
                print(" >>> Debugging: No words found in the sentence, skipping.")
                
                return (False, 0)

            # Let's see what sentence is before we process it.
            print(f" >>> Debugging: Sentence before processing: {sentence.text}")
            
            intent_response = process_sentence_for_possession_intent(sentence)

            if intent_response:
                # If we have a response, we can return it.
                print(f" >>> Debugging: Found intent response: {intent_response}")
                
                # We can also return the intent ID.
                intent_id = get_intent_id_by_protocol("user_informs_of_possession")
                
                return (intent_response, intent_id)

    # First, we do constituency parsing to identify the structure of the sentence and extract the intent via the main verb phrase.
    
    # Then, we do dependency parsing to extract the entities, their qualifiers and quantifiers.
    
    # Work on the verb 'to have' for the intent `user_informs_of_possession`.

    return (False, 0)
    

@app.route("/uni/send-chat", methods=["POST"])
def send_chat_route():
    
    user_input = request.form.get("user_prompt")
    
    # This is where we interrupt with the RegEx engine to check for any special commands.
    (regex_response, answer), intent_id  = process_regex_commands(user_input)
    
    intent = sql("SELECT * FROM intents WHERE int_id = ?", (intent_id,), single=True)
    
    if regex_response:
        
        msg_type = "regex"
        
        if isinstance(regex_response, tuple) or isinstance(regex_response, list):
            response = regex_response[0]
        else:
            response = regex_response
            
    else:
        
        (syntactic_parse_response, intent_id) = process_syntactic_parsing(user_input)

        if testing := False:  # Change this to True to test the syntactic parsing.
            return jsonify({
                "vbox": "Stopping here to test.",
            })
        
        if syntactic_parse_response:
            response = syntactic_parse_response
            msg_type = "syntactic"

        else:
            response = send_chat_with_llm(user_input)
            msg_type = "llm"

    # Reload intent.
    intent = sql("SELECT * FROM intents WHERE int_id = ?", (intent_id,), single=True)        
        
    metadata = {
        "int_id": intent_id,
        "int_protocol": intent['int_protocol'] if intent else None,
        "answer": answer,
    }
    
    metadata = json.dumps(metadata)
    
    # Insert the user's input into the database.
    sql("INSERT INTO messages (msg_role, msg_content, msg_metadata, int_id, msg_type) VALUES (?, ?, ?, ?, ?)", ("user", user_input, metadata, intent_id, msg_type, ))
    
    # Save the assistant's response to the database.
    sql("INSERT INTO messages (msg_role, msg_content, msg_type) VALUES (?, ?, ?)", ("assistant", response, msg_type, ))

    # Reload all messages from the database.
    db_messages = sql("SELECT * FROM messages WHERE sum_id = 0 ORDER BY msg_id ASC")
    
    summaries = sql("SELECT * FROM summaries ORDER BY sum_id DESC")
    
    # Return our JSON response.
    
    return jsonify({
        "htmls": {
            "#messages": render_template("messages.html", messages=db_messages, summaries=summaries)
        },
        "values": {
            "#user-input": "",
        },
        "js": ';scrollToTheTop();autosize.update($(".autosize"));$("#user-input").focus()',
    })


@app.route('/uni/summarize-conversation-prompt', methods=['POST'])
def summarize_conversation_prompt():
    
    return jsonify({
        "vbox": render_template('summarize_prompt.html'),
        "js": 'autosize($(".autosize"));',
    })
    
    
@app.route('/uni/generate-title', methods=['POST'])
def generate_title():
    
    db_messages = sql("SELECT * FROM messages WHERE sum_id = 0 ORDER BY msg_id ASC")

    message_stream = "\n\n".join([f"{msg['msg_role']}: {msg['msg_content']}" for msg in db_messages])

    messages = [
        {
            "role": "system", 
            "content": "You are a helpful assistant that generates titles for conversations."
        }, {
            "role": "user", 
            "content": f"""Generate a concise and descriptive title for the following conversation:\n{message_stream}.\n\nDo not include quotes or any other formatting. The title should be short, ideally no more than 10 words."""
        }
    ]

    title_completion = client.chat.completions.create(
        messages=messages,
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        temperature=0.1,
    )

    title = title_completion.choices[0].message.content.strip()
    
    return jsonify({
        'values': {
            '#summary-title': title,
        },
    })


@app.route('/uni/generate-summary', methods=['POST'])
def generate_summary():

    db_messages = sql("SELECT * FROM messages WHERE sum_id = 0 ORDER BY msg_id ASC")
    
    message_stream = "\n\n".join([f"{msg['msg_role']}: {msg['msg_content']}" for msg in db_messages])
    
    messages = [
        {
            "role": "system", 
            "content": "You are a helpful assistant that generates summaries for conversations."
        }, {
            "role": "user", 
            "content": f"Generate a concise and descriptive summary for the following conversation:\n{message_stream}.\n\nDo not include quotes or any other formatting."
        }
    ]
    
    summary_completion = client.chat.completions.create(
        messages=messages,
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        temperature=0.1,
    )

    summary = summary_completion.choices[0].message.content.strip()
    
    return jsonify({
        'values': {
            '#summary-content': summary,
        },
        "js": 'autosize($(".autosize"));',
    })
    
    
@app.route('/uni/show_summary/<int:summary_id>', methods=['POST'])
def show_summary(summary_id):

    summary = sql("SELECT * FROM summaries WHERE sum_id = ?", (summary_id,), single=True)

    messages = sql("SELECT * FROM messages WHERE sum_id = ?", (summary_id,))

    return jsonify({
        "vbox": render_template('summary.html', summary=summary, messages=messages),
    })


@app.route('/uni/summarize-conversation', methods=['POST'])
def summarize_conversation():
    
    summary_title = request.form['summary_title']
    summary_content = request.form['summary_content']

    # Insert the summary into the database.
    sum_id = sql("INSERT INTO summaries (sum_title, sum_content) VALUES (?, ?)", (summary_title, summary_content, ))

    # Update the messages to mark them as summarized and link them to the summary ID.
    sql("UPDATE messages SET sum_id = ? WHERE sum_id = 0", (sum_id,))

    return jsonify({
        'redirect': '/',
    })


@app.template_filter('datetimeformat')
def datetimeformat(value):
    return value.strftime("%a %b %#d, %Y @ %#I:%M %p")


@app.template_filter('escape_html_chars')
def escape_html_chars(text):

    if not text:
        return text

    # Check if the text has an image tag in it. If so, avoid that tag.
    if "<img" in text:
        return text

    return text.replace("<", "&lt;").replace(">", "&gt;")


def detect_code_language(code):
    
    if re.search(r'\bdef\b|\bimport\b|\bclass\b|\bself\b|#', code):
        return "python"
    elif re.search(r'<[a-zA-Z]+>|<\/[a-zA-Z]+>', code):
        return "html"
    elif re.search(r'{.*?}|[a-z-]+:\s*[^;]+;', code):
        return "css"
    elif re.search(r'\bfunction\b|\bvar\b|\blet\b|\bconst\b|=>', code):
        return "javascript"
    else:
        return "unknown"


@app.template_filter('singleticks')
def singleticks(text):

    def process_non_code_blocks(match):

        # Get the block from the match.
        block = match.group(0)

        # If the block starts with a code block, ignore it.
        if block.startswith("<code>"):

            # Ignore code blocks
            return block  # Ignore code blocks

        # Use regex to identify code blocks created by `singleticks` and other text
        return re.sub(r'`(.*?)`', r'<code>\1</code>', block)

    # Use regex to identify code blocks created by `tripleticks` and other text
    return re.sub(r'(<code>.*?</code>|[^<]+)', process_non_code_blocks, text, flags=re.DOTALL)


@app.template_filter('tripleticks')
def tripleticks(text):

    lines = text.splitlines()
    in_code_block = False
    result = []
    buffer = []  # To accumulate code content for language detection

    for line in lines:
        if line.startswith("```"):
            if in_code_block:
                language = detect_code_language("\n".join(buffer))
                result.append(f'<code class="{language}">' + "\n".join(buffer) + "</code>")
                buffer = []
                in_code_block = False
            else:
                in_code_block = True
        elif in_code_block:
            buffer.append(line)
        else:
            result.append(line)

    if in_code_block and buffer:
        language = detect_code_language("\n".join(buffer))
        result.append(f'<code class="{language}">' + "\n".join(buffer) + "</code>")

    return "\n".join(result)


@app.template_filter('replace_tabs_and_spaces')
def replace_tabs_and_spaces_raw(text):

    if not text:
        return text

    lines = text.splitlines()
    result = []

    for line in lines:
        # Replace spaces at the beginning of the line with &nbsp;
        leading_spaces = len(line) - len(line.lstrip(' '))
        line = '&nbsp;' * leading_spaces + line.lstrip(' ')

        # Replace \t with a tab element or two &nbsp;
        line = line.replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')

        result.append(line)

    return '\n'.join(result)


@app.template_filter('bold_asterisks')
def bold_asterisks(text):

    if not text:
        return text

    return_text = text
    return_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', return_text)
    # Make LI tags
    return_text = return_text.replace("&nbsp;&nbsp;&nbsp;&nbsp;* ", "&nbsp;&nbsp;&nbsp;&nbsp;<i class=\"fas fa-circle\"></i> ")
    # return_text = return_text.replace("* ", "<i class=\"fas fa-circle\"></i> ")

    return return_text


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5011)
    