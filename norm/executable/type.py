from sqlalchemy.orm import with_polymorphic
from sqlalchemy import desc, or_

from norm.executable import NormExecutable, NormError
from norm.models.natives import ListLambda
from norm.models.norm import Lambda, Variable, Status, retrieve_type


class TypeName(NormExecutable):

    DEFAULT_NAMESPACE = ''

    def __init__(self, name, version=None):
        """
        The type qualified name
        :param name: name of the type
        :type name: str
        :param version: version of the type
        :type version: int
        """
        super().__init__()
        self.namespace = None
        self.name = name
        self.version = version

    def __str__(self):
        return self.name + '@' + str(self.version or 'latest')

    def execute(self, session, user, context):
        """
        Retrieve the Lambda function by namespace, name, version.
        Note that user is encoded by the version.
        :rtype: Lambda
        """
        if self.namespace is not None:
            namespaces = [self.namespace]
        else:
            namespaces = context.namespaces
        lam = retrieve_type(namespaces, self.name, self.version, session)
        if lam is None:
            #  create a new Lambda
            lam = Lambda(namespace=self.namespace or self.DEFAULT_NAMESPACE,
                         name=self.name)
        return lam

"""
        if self.version is None:
            #  find the latest version
            lam = session.query(with_polymorphic(Lambda, '*')) \
                         .filter(Lambda.namespace.in_(namespaces),
                                 Lambda.name == self.name,
                                 Lambda.status == Status.READY) \
                         .order_by(desc(Lambda.version))\
                         .scalar()
        else:
            lam = session.query(with_polymorphic(Lambda, '*')) \
                         .filter(Lambda.namespace.in_(namespaces),
                                 Lambda.name == self.name,
                                 Lambda.status == Status.READY,
                                 Lambda.version == self.version)\
                         .scalar()
        # TODO: Check permissions for the user
"""



class ListType(NormExecutable):

    def __init__(self, intern):
        """
        The type of List with intern type
        :param intern: the type of the intern
        :type intern: TypeName
        """
        super().__init__()
        self.intern = intern

    def execute(self, session, user, context):
        """
        Return a list type
        :rtype: ListLambda
        """
        lam = self.intern.execute(session, user, context)
        if lam.id is None:
            raise NormError("{} does not seem to be declared yet".format(self.intern))

        q = session.query(ListLambda, Variable).join(ListLambda.variables)\
            .filter(Variable.type_id == lam.id)
        llam = q.scalar()
        if llam is None:
            # create a new ListLambda
            llam = ListLambda(lam)

        return llam
