from antlr4 import *
from collections import namedtuple
from norm.normLexer import normLexer
from norm.normParser import normParser
from norm.normListener import normListener

from antlr4.error.ErrorListener import ErrorListener


class NormErrorListener(ErrorListener):

    def __init__(self):
        super(NormErrorListener, self).__init__()

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        err_msg = "line " + str(line) + ":" + str(column) + " " + msg
        raise ValueError(err_msg)


TypeName = namedtuple('TypeName', ['namespace', 'name', 'version'])
ListType = namedtuple('ListType', ['intern'])
UnionType = namedtuple('UnionType', ['types'])
TypeDefinition = namedtuple('TypeDefinition', ['type_name', 'argument_declarations', 'output_type_name'])
TypeImpl = namedtuple('TypeImpl', ['mode', 'code'])
ArgumentDeclaration = namedtuple('ArgumentDeclaration', ['variable_name', 'variable_type'])
ArgumentDeclarations = namedtuple('ArgumentDeclarations', ['arguments'])
FullTypeDeclaration = namedtuple('FullTypeDeclaration', ['type_definition', 'type_implementation'])
IncrementalTypeDeclaration = namedtuple('IcrementalTypeDeclaration', ['type_name', 'type_implementation'])


class NormExecutor(normListener):
    def __init__(self):
        self.comments = ''
        self.imports = []
        self.namespace = ''
        self.stack = []
        self.results = None

    def exitDeclarationExpression(self, ctx:normParser.DeclarationExpressionContext):
        type_declaration = self.stack.pop()
        if isinstance(type_declaration, FullTypeDeclaration):
            # TODO declare type
            pass
        elif isinstance(type_declaration, IncrementalTypeDeclaration):
            # TODO add on type
            pass
        else:
            raise ValueError('Wrong declaration syntax')

    def exitFullTypeDeclaration(self, ctx: normParser.FullTypeDeclarationContext):
        type_implementation = self.stack.pop()
        type_definition = self.stack.pop()
        self.stack.append(FullTypeDeclaration(type_definition, type_implementation))

    def exitIncrementalTypeDeclaration(self, ctx:normParser.IncrementalTypeDeclarationContext):
        type_implementation = self.stack.pop()
        type_name = self.stack.pop()
        self.stack.append(IncrementalTypeDeclaration(type_name, type_implementation))

    def exitTypeName(self, ctx:normParser.TypeNameContext):
        typename = ctx.TYPENAME()
        if typename:
            version = ctx.version().getText() if ctx.version() else None
            self.stack.append(TypeName(self.namespace, str(typename), version))
        elif ctx.LSBR():
            self.stack.append(ListType(self.stack.pop()))
        elif ctx.OR():
            t1 = self.stack.pop()
            t2 = self.stack.pop()
            t = UnionType([])
            if isinstance(t1, UnionType):
                t.types.extend((tt for tt in t1.types if tt not in t))
            else:
                t.types.append(t1)
            if isinstance(t2, UnionType):
                t.types.extend((tt for tt in t2.types if tt not in t))
            else:
                t.types.append(t2)
            self.stack.append(t)
        else:
            raise ValueError('Not a valid type name definition')

    def exitVariableName(self, ctx:normParser.VariableNameContext):
        self.stack.append(ctx.getText())

    def exitArgumentDeclaration(self, ctx:normParser.ArgumentDeclarationContext):
        variable_name = self.stack.pop()
        type_name = self.stack.pop()
        self.stack.append(ArgumentDeclaration(variable_name, type_name))

    def exitArgumentDeclarations(self, ctx:normParser.ArgumentDeclarationsContext):
        arguments = []
        for arg in ctx.children:
            if isinstance(arg, normParser.ArgumentDeclarationContext):
                arguments.append(self.stack.pop())
        self.stack.append(ArgumentDeclarations(list(reversed(arguments))))

    def exitTypeDefinition(self, ctx:normParser.TypeDefinitionContext):
        output_type_name = None
        argument_declarations = None
        if ctx.CL():
            output_type_name = self.stack.pop()
        if ctx.LBR():
            argument_declarations = self.stack.pop()
        type_name = self.stack.pop()
        self.stack.append(TypeDefinition(type_name, argument_declarations, output_type_name))

    def exitTypeImplementation(self, ctx:normParser.TypeImplementationContext):
        if ctx.LCBR():
            self.stack.append(TypeImpl('query', ctx.code().getText()))
        elif ctx.PYTHON_BLOCK():
            self.stack.append(TypeImpl('python', ctx.code().getText()))
        elif ctx.KERAS_BLOCK():
            self.stack.append(TypeImpl('keras', ctx.code().getText()))
        else:
            raise ValueError('Only query, python, or keras code blocks are supported')

    def exitUpdateExpression(self, ctx:normParser.UpdateExpressionContext):
        query_result = self.stack.pop()
        # TODO update the query result to the database
        self.stack.append('Data {} for type {} have been updated at version {}')

    def exitDeleteExpression(self, ctx:normParser.DeleteExpressionContext):
        query_result = self.stack.pop()
        # TODO delete the query result from the database
        self.stack.append('Data {} for type {} have been deleted as version {}')

    def exitQueryExpression(self, ctx:normParser.QueryExpressionContext):
        query_expression = self.stack.pop()
        # TODO execute the query
        self.stack.append('Query result')

    def exitComment_contents(self, ctx: normParser.Comment_contentsContext):
        self.comments += ctx.getText()

    def exitComments(self, ctx: normParser.CommentsContext):
        content = ctx.getText()
        if content.startswith('//'):
            self.comments = content[2:]

    def exitNamespace(self, ctx: normParser.NamespaceContext):
        ns = ctx.namespace_name().getText()
        if ns:
            self.namespace = ns

    def exitImports(self, ctx: normParser.ImportsContext):
        ns = ctx.namespace_name().getText()
        if ns:
            self.imports.append(ns)

    def execute(self):
        pass


def trim_script(script):
    statements = script.split(';')
    if len(statements) > 1:
        to_compile = [s for s in statements if s.find("namespace") > -1 or s.find("import") > -1]
        last_statement = statements[-2] + ";"
        if last_statement.find("namespace") < 0 and last_statement.find("import") < 0:
            to_compile.append(last_statement)
        else:
            to_compile[-1] += ';'
        script = ';'.join(to_compile)
    return script


def compile_norm(script, last=True):
    """
    Compile the script
    :param script: the script to execute
    :type script: str
    :param last: compile the last statement, default to True
    :type last: bool
    :return: the executable
    :rtype: NormExecutable
    """
    script = script.strip(' \r\n\t')
    if last:
        script = trim_script(script)
    if script == '':
        return None

    lexer = normLexer(InputStream(script))
    stream = CommonTokenStream(lexer)
    parser = normParser(stream)
    parser.addErrorListener(NormErrorListener())
    tree = parser.script()
    executor = NormExecutor()
    ParseTreeWalker().walk(executor, tree)
    return executor


from superset import db
test = db.Table('test', db.Column('test1', db.Integer), primary_key=True)

db.session.query(test).filter(test.test1==2)
