import json
import string
import random
import gzip
from testconstants import DEWIKI, ENWIKI, ESWIKI, FRWIKI
from data import FIRST_NAMES, LAST_NAMES, DEPT, LANGUAGES
import itertools


class KVGenerator(object):
    def __init__(self, name, start, end):
        self.name = name
        self.start = start
        self.end = end
        self.current = start
        self.itr = start

    def setrange(self, args):
        self.itr = args['start']
        self.end = args['end']

    def getrange(self):
        return self.start, self.end

    def has_next(self):
        return self.itr < self.end

    def next(self, index = None):
        raise NotImplementedError

    def reset(self):
        self.itr = self.start

    def __iter__(self):
        return self

    def __len__(self):
        return self.end - self.start


class DocumentGenerator(KVGenerator):
    """ An idempotent document generator."""

    def __init__(self, name, template, *args, **kwargs):
        """Initializes the document generator

        Example:
        Creates 10 documents, but only iterates through the first 5.

        age = range(5)
        first = ['james', 'sharon']
        template = '{{ "age": {0}, "first_name": "{1}" }}'
        gen = DocumentGenerator('test_docs', template, age, first, start=0, end=5)

        Args:
            name: The key name prefix
            template: A formated string that can be used to generate documents
            *args: A list for each argument in the template
            *kwargs: Special constrains for the document generator
        """
        self.args = args
        self.template = template

        size = 0
        if not len(self.args) == 0:
            size = 1
            for arg in self.args:
                size *= len(arg)

        if 'start' in kwargs:
            self.start = kwargs['start']

        if 'end' in kwargs:
            self.end = kwargs['end']

        super(DocumentGenerator, self).__init__(name, self.start, self.end)

    """Creates the next generated document and increments the iterator.

    Returns:
        The document generated"""

    def next(self):
        if self.itr >= self.end:
            raise StopIteration
        seed = self.itr
        doc_args = []
        for arg in self.args:
            value = arg[seed % len(arg)]
            doc_args.append(value)
            seed /= len(arg)

        json_doc = json.loads(self.template.format(*doc_args).replace('\'', '"').replace('True', 'true').replace('False', 'false'))
        json_doc['_id'] = self.name + '-' + str(self.itr)
        json_doc['mutated'] = 0
        self.itr += 1
        return json_doc['_id'], json.dumps(json_doc).encode("ascii", "ignore")



class SubdocDocumentGenerator(KVGenerator):
    """ An idempotent document generator."""

    def __init__(self, name, template, *args, **kwargs):
        """Initializes the document generator

        Example:
        Creates 10 documents, but only iterates through the first 5.

        age = range(5)
        first = ['james', 'sharon']
        template = '{{ "age": {0}, "first_name": "{1}" }}'
        gen = DocumentGenerator('test_docs', template, age, first, start=0, end=5)

        Args:
            name: The key name prefix
            template: A formated string that can be used to generate documents
            *args: A list for each argument in the template
            *kwargs: Special constrains for the document generator
        """
        self.args = args
        self.template = template

        print type(self.template)

        size = 0
        if not len(self.args) == 0:
            size = 1
            for arg in self.args:
                size *= len(arg)

        if 'start' in kwargs:
            self.start = kwargs['start']

        if 'end' in kwargs:
            self.end = kwargs['end']

        super(SubdocDocumentGenerator, self).__init__(name, self.start, self.end)

    """Creates the next generated document and increments the iterator.

    Returns:
        The document generated"""
    def next(self):
        if self.itr >= self.end:
            raise StopIteration
        self.itr += 1
        return self.name + '-' + str(self.itr), json.dumps(self.template).encode("ascii", "ignore")

class BlobGenerator(KVGenerator):
    def __init__(self, name, seed, value_size, start=0, end=10000):
        super(BlobGenerator, self).__init__(name, start, end)
        self.seed = seed
        self.value_size = value_size

    def next(self):
        self.current = self.itr
        key = self.name + str(self.itr)
        if self.value_size == 1:
            value = random.choice(string.letters)
        else:
            value = self.seed + str(self.itr)
            extra = self.value_size - len(value)
            if extra > 0:
                value += 'a' * extra
        self.itr += 1
        return key, value

class BatchedDocumentGenerator(object):

    def __init__(self, document_generator, batch_size_int=100):
        self._doc_gen = document_generator
        self._batch_size = batch_size_int
        if self._batch_size <= 0:
            raise ValueError("Invalid Batch size {0}".format(self._batch_size))

    def get_docgen(self):
        return self._doc_gen

    def getrange(self):
        return self._doc_gen.getrange()

    def setrange(self, args):
        self._doc_gen.setrange(args)

    def has_next(self):
        return self._doc_gen.has_next()

    def next_batch(self):
        count = 0
        key_val = {}
        while count < self._batch_size and self.has_next():
            key, val = self._doc_gen.next()
            key_val[key] = val
            count += 1
        return key_val


class JSONNonDocGenerator(KVGenerator):
    """
    Values can be arrays, integers, strings
    """
    def __init__(self, name, values, start=0, end=10000):
        super(JSONNonDocGenerator, self).__init__(name, start, end)
        self.values = values

    def next(self):
        key = self.name + str(self.itr)
        index = self.itr
        while index > len(self.values):
            index = index - len(self.values)
        value = json.dumps(self.values[index-1])
        self.itr += 1
        return key, value

class Base64Generator(KVGenerator):
    def __init__(self, name, values, start=0, end=10000):
        KVGenerator.__init__(self, name, start, end)
        self.values = values

    def next(self):
        self.current = self.itr
        key = self.name + str(self.itr)
        index = self.itr
        while index > len(self.values):
            index = index - len(self.values)
        value = self.values[index-1]
        self.itr += 1
        return key, value

class JsonDocGenerator(KVGenerator):

    def __init__(self, name, op_type="create", encoding="utf-8", *args, **kwargs ):
        """Initializes the JSON document generator
        gen =  JsonDocGenerator(prefix, encoding="utf-8",start=0,end=num_items)

        Args:
            prefix: prefix for key
            encoding: utf-8/ascii/utf-16 encoding of JSON doc
            *args: A list for each argument in the template
            *kwargs: Special constrains for the document generator

        Sample doc:
                    {
                      "salary": 75891.68,
                      "name": "Safiya Morgan",
                      "dept": "Support",
                      "is_manager": true,
                      "mutated": 0,
                      "join_date": "1984-05-22 07:28:00",
        optional-->   "manages": {
                        "team_size": 6,
                        "reports": [
                          "Basha Taylor",
                          "Antonia Cox",
                          "Winta Campbell",
                          "Lilith Scott",
                          "Beryl Miller",
                          "Ambika Reed"
                        ]
                      },
                      "languages_known": [
                        "English",
                        "Spanish",
                        "German"
                      ],
                      "emp_id": 10000001,
                      "email": "safiya_1@mcdiabetes.com"
                    }
        """
        self.args = args
        self.name = name
        self.gen_docs = {}
        self.encoding = encoding

        size = 0
        if not len(self.args) == 0:
            size = 1
            for arg in self.args:
                size *= len(arg)

        random.seed(0)
        self.op_type = op_type

        if 'start' in kwargs:
            self.start = int(kwargs['start'])

        if 'end' in kwargs:
            self.end = int(kwargs['end'])
        super(JsonDocGenerator, self).__init__(name, self.start, self.end)

    def generate_data(self):
        if self.op_type == "create":
            emp_name = self.generate_name()
            doc_dict = {
                        'emp_id': str(10000000+int(self.itr)),
                        'name': emp_name,
                        'dept': self.generate_dept(),
                        'email': "%s@mcdiabetes.com" %
                                 (emp_name.split(' ')[0].lower()),
                        'salary': self.generate_salary(),
                        'join_date': self.generate_join_date(),
                        'languages_known': self.generate_lang_known(),
                        'is_manager': bool(random.getrandbits(1)),
                        'mutated': 0,
                        'type': 'emp'
                       }
            if doc_dict["is_manager"]:
                doc_dict['manages'] = {'team_size': random.randint(5, 10)}
                doc_dict['manages']['reports'] = []
                for _ in xrange(0, doc_dict['manages']['team_size']):
                    doc_dict['manages']['reports'].append(self.generate_name())
            return doc_dict
        elif self.op_type == "delete":
            # for deletes, just keep/return empty docs with just type field
            self.gen_docs = {'type': 'emp' for count in range(self.start, self.end)}

    def update(self, fields_to_update=None):
        """
            Updates the fields_to_update in the document.
            @param fields_to_update is usually a list of fields one wants to
                   regenerate in a doc during update. If this is 'None', by
                   default for this dataset, 'salary' field is regenerated.
        """
        random.seed(1)
        for count in xrange(self.start, self.end):
            doc_dict = self.gen_docs[count]
            if fields_to_update is None:
                doc_dict['salary'] = self.generate_salary()
            else:
                if 'salary' in fields_to_update:
                    doc_dict['salary'] = self.generate_salary()
                if 'dept' in fields_to_update:
                    doc_dict['dept'] = self.generate_dept()
                if 'is_manager' in fields_to_update:
                    doc_dict['is_manager'] = bool(random.getrandbits(1))
                    if doc_dict["is_manager"]:
                        doc_dict['manages'] = {'team_size': random.randint(5,10)}
                        doc_dict['manages']['reports'] = []
                        for _ in xrange(0, doc_dict['manages']['team_size']):
                            doc_dict['manages']['reports'].append(self.generate_name())
                if 'languages_known' in fields_to_update:
                    doc_dict['languages_known'] = self.generate_lang_known()
                if 'email' in fields_to_update:
                    doc_dict['email'] = "%s_%s@mcdiabetes.com" %\
                                        (doc_dict['name'].split(' ')[0].lower(),
                                         str(random.randint(0,99)))
                if 'manages.team_size' in fields_to_update or\
                        'manages.reports' in fields_to_update:
                    doc_dict['manages'] = {}
                    doc_dict['manages']['team_size'] = random.randint(5, 10)
                    doc_dict['manages']['reports'] = []
                    for _ in xrange(0, doc_dict['manages']['team_size']):
                        doc_dict['manages']['reports'].append(self.generate_name())
            self.gen_docs[count] = doc_dict

    def next(self):
        self.itr += 1
        doc = self.generate_data()
        return self.name+str(10000000+self.itr),\
               json.dumps(doc).encode(self.encoding, "ignore")

    def generate_join_date(self):
        import datetime
        year = random.randint(1950, 2016)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        hour = random.randint(0,23)
        min = random.randint(0,59)
        return datetime.datetime(year, month, day, hour, min).isoformat()

    def generate_dept(self):
        return DEPT[random.randint(0, len(DEPT)-1)]

    def generate_salary(self):
        return round(random.random()*100000 + 50000, 2)

    def generate_name(self):
        return "%s %s" %(FIRST_NAMES[random.randint(1, len(FIRST_NAMES)-1)],
                         LAST_NAMES[random.randint(1, len(LAST_NAMES)-1)])

    def generate_lang_known(self):
        count = 0
        lang = []
        while count < 3:
            lang.append(LANGUAGES[random.randint(0, len(LANGUAGES)-1)])
            count += 1
        return lang

class WikiJSONGenerator(KVGenerator):

    def __init__(self, name, lang='EN', encoding="utf-8", op_type="create",
                 *args, **kwargs):

        """Wikipedia JSON document generator

        gen = WikiJSONGenerator(prefix, lang="DE","encoding="utf-8",
                                start=0,end=1000)
        Args:
            prefix: prefix for key
            encoding: utf-8/ascii/utf-16 encoding of JSON doc
            *args: A list for each argument in the template
            *kwargs: Special constrains for the document generator

        ** For EN, generates 20000 unique docs, and then duplicates docs **
        ** For ES, DE and FR, generates 5000 unique docs and then duplicates **


        Sample EN doc:

        {
           "revision": {
              "comment": "robot Modifying: [[bar:Apr\u00fc]]",
              "timestamp": "2010-05-13T20:42:11Z",
              "text": {
                 "@xml:space": "preserve",
                 "#text": "'''April''' is the fourth month of the year with 30
                 days. The name April comes from that Latin word ''aperire''
                 which means \"to open\". This probably refers to growing plants
                 in spring. April begins on the same day of week as ''[[July]]''
                 in all years and also ''[[January]]'' in leap years.\n\nApril's
                flower is the Sweet Pea and ...<long text>
                },
              "contributor": {
                 "username": "Xqbot",
                 "id": "40158"
              },
              "id": "2196110",
              "minor": null
           },
           "id": "1",
           "title": "April"
           "mutated": 0,
        }


        """

        self.args = args
        self.name = name
        self.gen_docs = {}
        self.encoding = encoding
        self.lang = lang

        size = 0
        if not len(self.args) == 0:
            size = 1
            for arg in self.args:
                size *= len(arg)

        KVGenerator.__init__(self, name, 0, size)
        random.seed(0)

        if 'start' in kwargs:
            self.start = int(kwargs['start'])

        if 'end' in kwargs:
            self.end = int(kwargs['end'])

        if op_type == "create":
            self.readiter = self.read_from_wiki_dump()
        elif op_type == "delete":
            # for deletes, just keep/return empty docs with just type field
            for count in xrange(self.start, self.end):
                self.gen_docs[count] = {'type': 'wiki'}

    def setrange(self, args):
        self.itr = args['start']
        self.end = args['end']
        '''
        I have mentioned 500 to make sure all reads the each 500 lines
        '''
        self.readiter = itertools.islice(self.readiter, 500 * args['counter'])

    def read_from_wiki_dump(self):

        done = False
        while not done:
            try:
                with gzip.open("lib/couchbase_helper/wiki/{0}wiki.txt.gz".
                                format(self.lang.lower()), "r") as f:
                    for doc in f:
                        yield doc
                    done = True
            except IOError:
                lang = self.lang.lower()
                wiki = eval("{0}WIKI".format(self.lang))
                print ("Unable to find file lib/couchbase_helper/wiki/"
                       "{0}wiki.txt.gz. Downloading from {1}...".
                       format(lang, wiki))
                import urllib
                urllib.URLopener().retrieve(
                    wiki,
                    "lib/couchbase_helper/wiki/{0}wiki.txt.gz".format(lang))
                print "Download complete!"

    def next(self):
        doc = self.readiter.next()
        doc['mutated'] = 0
        doc['type'] = 'wiki'
        self.itr += 1
        return self.name+str(10000000+self.itr),\
               json.dumps(doc, indent=3).encode(self.encoding, "ignore")
