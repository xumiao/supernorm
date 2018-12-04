"""A collection of ORM sqlalchemy models for Lambda"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from datetime import datetime
from textwrap import dedent
import enum

from future.standard_library import install_aliases

from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean, DateTime, Enum, desc, UniqueConstraint
from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, with_polymorphic

from norm.models.mixins import lazy_property, ParametrizedMixin, new_version
from norm.utils import current_user
import norm.config as config

from pandas import DataFrame
import pandas as pd

import traceback
import logging
logger = logging.getLogger(__name__)

install_aliases()

Model = config.Model
metadata = Model.metadata
user_model = config.user_model


class Variable(Model, ParametrizedMixin):
    """Variable placeholder"""

    __tablename__ = 'variables'

    id = Column(Integer, primary_key=True)
    name = Column(String(256), default='')
    type_id = Column(Integer, ForeignKey('lambdas.id'))
    type_ = relationship('Lambda', foreign_keys=[type_id])

    def __init__(self, name, type_):
        """
        Construct the variable
        :param name: the full name of the variable
        :type name: str
        :param type_: the type of the variable
        :type type_: Lambda
        """
        self.id = None
        self.name = name
        self.type_ = type_


class RevisionMode(enum.Enum):
    NEW = 0
    OR = 1
    AND = 2


class Revision(Model, ParametrizedMixin):
    """Revision of the Lambda. All revisions for the same version are executed in memory."""
    __tablename__ = 'revisions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    mode = Column(Enum(RevisionMode), default=RevisionMode.NEW, nullable=False)
    query = Column(Text, default='')

    def apply(self, lam):
        """
        Apply revision on the given Lambda
        :param lam: the Lambda function to be applied on
        :type lam: Lambda
        :return: the revised Lambda
        :rtype: Lambda
        """
        pass

    def redo(self, lam):
        """
        Re-apply revision on the given Lambda
        :param lam: the Lambda function to be applied on
        :type lam: Lambda
        :return: the revised Lambda
        :rtype: Lambda
        """
        pass

    def undo(self, lam):
        """
        Revert the revision of the given Lambda
        :param lam: the Lambda function to be reverted on
        :type lam: Lambda
        :return: the reverted Lambda
        :rtype: Lambda
        """
        pass


lambda_revision = Table(
    'lambda_revision', metadata,
    Column('id', Integer, primary_key=True),
    Column('lambda_id', Integer, ForeignKey('lambdas.id')),
    Column('revision_id', Integer, ForeignKey('revisions.id')),
)

lambda_variable = Table(
    'lambda_variable', metadata,
    Column('id', Integer, primary_key=True),
    Column('lambda_id', Integer, ForeignKey('lambdas.id')),
    Column('variable_id', Integer, ForeignKey('variables.id'))
)


class Status(enum.Enum):
    DRAFT = 0
    READY = 1


def default_version(context):
    params = context.get_current_parameters()
    namespace = params['namespace']
    name = params['name']
    return new_version(namespace, name)


class Lambda(Model, ParametrizedMixin):
    """Lambda model is a function"""
    __tablename__ = 'lambdas'
    category = Column(String(128))

    OUTPUT_NAME = 'output'

    # identifiers
    id = Column(Integer, primary_key=True, autoincrement=True)
    namespace = Column(String(512), default='')
    name = Column(String(256), nullable=False)

    # owner
    created_by_id = Column(Integer, ForeignKey(user_model.id))
    owner = relationship(user_model, backref='lambdas', foreign_keys=[created_by_id])
    # auditing
    created_on = Column(DateTime, default=datetime.now)
    changed_on = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    # schema
    description = Column(Text, default='')
    variables = relationship(Variable, secondary=lambda_variable)
    # version
    anchor = Column(Boolean, default=True)
    cloned_from_id = Column(Integer, ForeignKey('lambdas.id'))
    cloned_from = relationship('Lambda', remote_side=[id])
    merged_from_ids = Column(ARRAY(Integer))
    version = Column(Integer, default=default_version, nullable=False)
    # revision
    revisions = relationship(Revision, secondary=lambda_revision)
    current_revision = Column(Integer, default=0)
    status = Column(Enum(Status), default=Status.DRAFT)

    __mapper_args__ = {
        'polymorphic_identity': 'lambda',
        'polymorphic_on': category
    }

    __table_args__ = tuple(UniqueConstraint('namespace', 'name', 'version', name='unique_lambda'))

    def __init__(self, namespace='', name='', description='', params='{}', variables=None):
        self.id = None
        self.namespace = namespace
        self.name = name
        self.version = None
        self.description = description
        self.params = params
        self.owner = current_user()
        self.status = Status.DRAFT
        self.merged_from_ids = []
        if variables is None:
            self.variables = []
        else:
            self.variables = variables

    @hybrid_property
    def nargs(self):
        return len(self.variables)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return self.signature

    @property
    def signature(self):
        if self.namespace:
            return '@'.join((self.namespace + '.' + self.name, str(self.version)))
        else:
            return '@'.join((self.name, str(self.version)))

    def clone(self):
        """
        Clone itself and bump up the version. Make sure updates are done after clone.
        :return: the cloned version of it
        :rtype: Lambda
        """
        lam = self.__class__(namespace=self.namespace, name=self.name, description=self.description,
                             params=self.params, variables=self.variables)
        lam.cloned_from = self
        lam.anchor = False
        return lam

    def merge(self, others):
        """
        Clone itself and merge several other versions into the new version
        :param others: other versions
        :type others: List[Lambda]
        :return: the merged version
        :rtype: Lambda
        """
        assert(all([o.namespace == self.namespace and o.name == self.name for o in others]))

        lam = self.clone()
        lam.merged_from_ids = [o.id for o in others]

        # TODO: merge implementation
        return lam

    def conjunction(self):
        """
        Revise with conjunction
        :return:
        """
        pass

    def disjunction(self):
        """
        Revise with disjunction
        :return:
        """
        pass

    def add(self, name, type_):
        """
        Add a new variable into the signature
        :type name: str
        :type type_: Lambda
        :return:
        """
        pass

    def delete(self, name):
        """
        Delete a variable from the signature
        :type name: str
        :return:
        """
        pass

    def rename(self, old_name, new_name):
        """
        Change the variable name
        :type old_name: str
        :type new_name: str
        :return:
        """
        pass

    def astype(self, name, new_type):
        """
        Change the type of the variable
        :type name: str
        :type new_type: Lambda
        :return:
        """
        pass

    def save(self, overwrite=False):
        """
        Save the current version and make it ready
        :param overwrite: whether to overwrite the existing object
        :type overwrite: Boolean
        :return:
        """
        pass

    def compact(self):
        """
        Compact this version with previous versions to make it an anchor
        :return:
        """
        pass

    def rollback(self):
        """
        Rollback to the previous revision if it is in draft status
        :return:
        """
        pass

    def forward(self):
        """
        Forward to the next revision if it is in draft status
        :return:
        """
        pass

    def __call__(self, *args, **kwargs):
        """
        TODO: implement
        """
        pass

    @property
    def data_file(self):
        root = config.DATA_STORAGE_ROOT
        return '{}/{}/{}.parquet'.format(root, self.namespace, self.name)

    def load_data(self):
        """
        Load data if it exists. If the current version is not an anchor, the previous versions will be combined.
        :return: the combined data
        :rtype: DataFrame
        """
        blocks = []
        lam = self
        while not lam.anchor:
            blocks.append(lam)
            if lam.cloned_from is None:
                msg = 'Can not find the anchor version for {}.{} before the chain is broken\n' \
                          .format(lam.namespace, lam.name) + \
                      '{}'.format([l.version for l in blocks])
                raise RuntimeError(msg)
            lam = lam.cloned_from
        blocks.append(lam)

        # TODO merge the data blocks together
        df = DataFrame()
        return df

    def query(self, assignments=None, filters=None, projections=None):
        if projections is None:
            df = pd.read_parquet(self.data_file)
        else:
            df = pd.read_parquet(self.data_file, columns=[col[0] for col in projections])
            df = df.rename(columns=dict(projections))
        if filters:
            projections = dict(projections)
            from norm.literals import COP
            for col, op, value in filters:
                pcol = projections.get(col, col)
                df = df[df[pcol].notnull()]
                if op == COP.LK:
                    df = df[df[pcol].str.contains(value.value)]
                elif op == COP.GT:
                    df = df[df[pcol] > value.value]
                elif op == COP.GE:
                    df = df[df[pcol] >= value.value]
                elif op == COP.LT:
                    df = df[df[pcol] < value.value]
                elif op == COP.LE:
                    df = df[df[pcol] <= value.value]
                elif op == COP.EQ:
                    df = df[df[pcol] == value.value]
                elif op == COP.NE:
                    if value.value is not None:
                        df = df[df[pcol] != value.value]
                elif op == COP.IN:
                    # TODO: Wrong
                    df = df[df[pcol].isin(value.value)]
                elif op == COP.NI:
                    # TODO: Wrong
                    df = df[~df[pcol].isin(value.value)]
        return df


class KerasLambda(Lambda):

    __mapper_args__ = {
        'polymorphic_identity': 'lambda_keras'
    }

    @lazy_property
    def keras_model(self):
        return None

    def __call__(self, *args, **kwargs):
        """
        TODO: implement
        """
        pass


class PythonLambda(Lambda):
    APPLY_FUNC_NAME = 'apply'

    __mapper_args__ = {
        'polymorphic_identity': 'lambda_python'
    }

    @lazy_property
    def apply_func(self):
        try:
            d = {}
            exec(dedent(self.code), d)
            return d.get(self.APPLY_FUNC_NAME)  # Should fail if the definition does not exist
        except:
            msg = 'Can not load apply function for {} : {} '.format(str(self), self.code)
            logger.error(msg)
            logger.debug(traceback.print_exc())
            raise RuntimeError(msg)

    def __call__(self, *args, **kwargs):
        """
        TODO: implement
        """
        pass


def retrieve_type(namespaces, name, version, session, status=None):
    """
    Retrieving a Lambda
    :type namespaces: str, List[str] or None
    :type name: str
    :type version: int or None
    :type session: sqlalchemy.orm.Session
    :type status: Status or None
    :return: the Lambda or None
    """
    #  find the latest versions
    queries = [Lambda.name == name]
    if status is not None and isinstance(status, Status):
        queries.append(Lambda.status == status)
    if namespaces is not None:
        if isinstance(namespaces, str):
            queries.append(Lambda.namespace == namespaces)
        else:
            queries.append(Lambda.namespace.in_(namespaces))
    if version is not None and isinstance(version, int):
        queries.append(Lambda.version <= version)
    lams = session.query(with_polymorphic(Lambda, '*')) \
                  .filter(*queries) \
                  .order_by(desc(Lambda.version)) \
                  .all()
    if len(lams) == 0:
        return None

    lam = lams[0]  # type: Lambda
    if version is not None and lam.version < version:
        msg = 'The specified version {} does not exist for {}.{}'.format(version, lam.namespace, lam.name)
        raise RuntimeError(msg)

    assert(lam is None or isinstance(lam, Lambda))
    return lam