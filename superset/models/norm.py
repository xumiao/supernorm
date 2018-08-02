"""A collection of ORM sqlalchemy models for Lambda"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from textwrap import dedent

from future.standard_library import install_aliases

from flask_appbuilder import Model

from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean
from sqlalchemy import Table
from sqlalchemy.ext.hybrid import hybrid_property

from sqlalchemy.orm import relationship

from superset import app, utils
from superset import security_manager as sm

from superset.models.helpers import AuditMixinNullable
from superset.models.mixins import VersionedMixin, lazy_property, ParametrizedMixin
from superset.models.core import metadata

from pandas import DataFrame
import traceback
import logging
logger = logging.getLogger(__name__)

install_aliases()

config = app.config


class Variable(Model):
    """Variable placeholder"""

    __tablename__ = 'variables'

    id = Column(Integer, primary_key=True)
    fullname = Column(String(256), nullable=False)
    name = Column(String(256), default='')
    attribute = Column(String(256), default='')
    as_input = Column(Boolean, default=True)
    as_output = Column(Boolean, default=True)
    type_id = Column(Integer, ForeignKey('lambdas.id'))
    type_ = relationship('Lambda', foreign_keys=[type_id])

    def __init__(self, fullname, type_, as_input=True, as_output=True):
        """
        Construct the variable
        :param fullname: the full name of the variable
        :type fullname: str
        :param type_: the type of the variable
        :type type_: Lambda
        """
        self.fullname = fullname
        na = fullname.split('.')
        self.name = na[0]
        if len(na) == 2:
            self.attribute = na[1]
        if len(na) > 2:
            msg = 'variable name can only take one level attribute, i.e., <name>.<attribute>, ' \
                  'but got multiple levels {}'.format(fullname)
            logger.error(msg)
            logger.debug(traceback.print_exc())
            raise ValueError(msg)
        self.type_ = type_
        self.as_input = as_input
        self.as_output = as_output

    @property
    def type_signature(self):
        signature = '-' if not self.as_input and self.as_output else ''
        signature += str(self.type_id) or self.type_.signature
        return signature

    def get(self, mem):
        """
        Retrieve value from the memory for this variable, if not in memory, return the default defined by type.
        :param mem: the memory holds the values
        :type mem: DataFrame
        :return: the value
        :rtype: DataFrame
        """
        return self.type_.get_values(mem, self.fullname)

    def set(self, mem, values):
        """
        Set values to the memory for this variable
        :param mem: the memory holds the value
        :type mem: DataFrame
        :param values: the value to set
        :type values: DataFrame
        :return: the memory
        :rtype: DataFrame
        """
        self.type_.set_values(mem, self.fullname, values)
        return mem


lambda_user = Table(
    'lambda_user', metadata,
    Column('id', Integer, primary_key=True),
    Column('lambda_id', Integer, ForeignKey('lambdas.id')),
    Column('user_id', Integer, ForeignKey('ab_user.id')),
)

lambda_variable = Table(
    'lambda_variable', metadata,
    Column('id', Integer, primary_key=True),
    Column('lambda_id', Integer, ForeignKey('lambdas.id')),
    Column('variable_id', Integer, ForeignKey('variables.id'))
)


class Lambda(Model, AuditMixinNullable, VersionedMixin, ParametrizedMixin):
    """Lambda model is a function"""

    __tablename__ = 'lambdas'
    description = Column(Text, default='')
    perm = Column(String(1024))
    code = Column(Text, default='')
    category = Column(String(128))
    owners = relationship(sm.user_model, secondary=lambda_user)
    variables = relationship(Variable, secondary=lambda_variable)

    __mapper_args__ = {
        'polymorphic_identity': 'lambda',
        'polymorphic_on': category
    }

    def __init__(self, namespace='', name='', version=None, description='', params='', code='',
                 variables=None, user=None):
        super(Lambda, self).__init__(namespace=namespace, name=name, version=version)
        self.description = description
        self.params = params
        self.code = code
        if user:
            self.creator = user
            self.owners = [user]
        if variables is None:
            self.variables = []
        else:
            self.variables = variables

    @hybrid_property
    def nargs(self):
        return len(self.variables)

    @hybrid_property
    def signature(self):
        return '{}({})[{}]'.format(self.fully_qualified_name, self.creator.username, self.type_signature)

    @property
    def type_signature(self):
        return ','.join((var.type_signature for var in self.variables))

    def clone(self, user=None):
        """
         Clone a Lambda
         :return: the cloned version of the Lambda
         :rtype: Lambda
         """
        return self.__class__(namespace=self.namespace,
                              name=self.name,
                              description=self.description,
                              params=self.params,
                              code=self.code,
                              variables=self.variables,
                              user=user or self.creator)

    @property
    def description_markeddown(self):
        return utils.markdown(self.description)

    def __call__(self, *args, **kwargs):
        """
        TODO: implement
        """
        pass

    def set_values(self, mem, variable_name, values):
        """
        Set values of current type to the memory by the variable name
        :param mem: the memory to store the values
        :type mem: DataFrame
        :param variable_name: the variable name
        :type variable_name: str
        :param values: the values to store in the memory
        :type values: DataFrame
        """
        pass

    def get_values(self, mem, variable_name):
        """
        Get values of current type to the memory by the variable name
        :param mem: the memory to store the values
        :type mem: DataFrame
        :param variable_name: the variable name
        :type variable_name: str
        """
        pass


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

