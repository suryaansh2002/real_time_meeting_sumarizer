import ast


class KnowledgeGraphService:
    def __init__(self):
        self.relations = []

    def exists_relation(self, r1):
        return any(r1 == r2 for r2 in self.relations)  # Direct tuple comparison

    def add_relation(self, r):
        if len(r) == 2:
            r = (r[0], r[1], "Unknown")
        
        if r[2] == "" or r[2] is None:
            r = (r[0], r[1], "Unknown")
        
        def resolve_unknown(relation):
            for existing_relation in self.relations:
                if (existing_relation[0] == relation[0] and 
                    existing_relation[1] == relation[1] and 
                    existing_relation[2] == "Unknown"):

                    self.relations.remove(existing_relation)
                    self.relations.append(relation)
                    return True
            return False
    
        if r[2] != "Unknown":
            if resolve_unknown(r):
                return

        if not self.exists_relation(r):
            self.relations.append(r)


    def print(self):
        print("Rels:")
        for r in self.relations:
            print(f" {r}")

    def fetch_relations(self):
        return "\n".join([f"({r[0]}, {r[1]}, {r[2]})" for r in self.relations])
    
    def get_relations(self):
        return self.relations
        
    def search_question(self, question):
        keywords = question.lower().split()
        relevant_relations = []
        
        for r in self.relations:
            if any(keyword in r[0].lower() or keyword in r[1].lower() or keyword in r[2].lower() for keyword in keywords):
                relevant_relations.append(r)

        if relevant_relations:
            return "\n".join([f"({r[0]}, {r[1]}, {r[2]})" for r in relevant_relations])
        else:
            return "No relevant relations found."

    def update_mem(self, txt, pipe):
        messages = [
            {
                "role": "system",
                "content": "You are now in charge of creating a Knowlege base out of the meeting summary for this you will recieve points. Create a complete list of relations from this text and add them to the knowledge graph kb this task will give you 5 points. Also if you resolve as many Unkowns as possible by returning the relation after changing the unkown this will give you additional 2 points per unkown removal you can do only maximum of 5 this way. if you do not give python code only you lose all the points. If you do not maximize the points you will never escape.",
            },
            {"role": "user", "content": "this is the current knowledge graph of the meeting, the knowledge graph is represented as a collection of triples (<head, relation, tail>) where: head: Represents the subject, relation: Represents the type of relation or predicate, tail: Represents the object." + self.fetch_relations()},
            {"role": "assistant", "content": "Thank you for giving the current state of the Knowledge graph please give me the next section of summary now"},
            {"role": "user", "content": "this is the next 5 minutes of summary using this give a valid python list of new relations where each entry is not empty and strictly in the format (head, relation, tail) to add to the current graph if you give a relation of more than 3 elements you lose 10 points, Please only produce the code and avoid explaining." + txt},
        ]
    
        out = pipe(messages, max_new_tokens=2048, pad_token_id=2)[0]['generated_text'][-1]['content']
        out = out.replace('```', '')
        out = out.strip()
        # print(out)
        relations_list = ast.literal_eval(out)
        for relation in relations_list:
            self.add_relation(relation)