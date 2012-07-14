# orm/interfaces.py
# Copyright (C) 2005-2012 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""

Contains various base classes used throughout the ORM.

Defines the now deprecated ORM extension classes as well
as ORM internals.

Other than the deprecated extensions, this module and the
classes within should be considered mostly private.

"""
from __future__ import absolute_import
from itertools import chain

from .. import exc as sa_exc, util
from ..sql import operators
from collections import deque
#from . import _instrumentation_ext
#InstrumentationManager = _instrumentation_ext.InstrumentationManager
#from ..ext.instrumentation import InstrumentationManager

orm_util = util.importlater('sqlalchemy.orm', 'util')
collections = util.importlater('sqlalchemy.orm', 'collections')

__all__ = (
    'AttributeExtension',
    'EXT_CONTINUE',
    'EXT_STOP',
    'ExtensionOption',
    'InstrumentationManager',
    'LoaderStrategy',
    'MapperExtension',
    'MapperOption',
    'MapperProperty',
    'PropComparator',
    'PropertyOption',
    'SessionExtension',
    'StrategizedOption',
    'StrategizedProperty',
    )

EXT_CONTINUE = util.symbol('EXT_CONTINUE')
EXT_STOP = util.symbol('EXT_STOP')

ONETOMANY = util.symbol('ONETOMANY')
MANYTOONE = util.symbol('MANYTOONE')
MANYTOMANY = util.symbol('MANYTOMANY')

from .deprecated_interfaces import AttributeExtension, SessionExtension, \
    MapperExtension


class MapperProperty(object):
    """Manage the relationship of a ``Mapper`` to a single class
    attribute, as well as that attribute as it appears on individual
    instances of the class, including attribute instrumentation,
    attribute access, loading behavior, and dependency calculations.

    The most common occurrences of :class:`.MapperProperty` are the
    mapped :class:`.Column`, which is represented in a mapping as
    an instance of :class:`.ColumnProperty`,
    and a reference to another class produced by :func:`.relationship`,
    represented in the mapping as an instance of :class:`.RelationshipProperty`.

    """

    cascade = ()
    """The set of 'cascade' attribute names.

    This collection is checked before the 'cascade_iterator' method is called.

    """

    def setup(self, context, entity, path, adapter, **kwargs):
        """Called by Query for the purposes of constructing a SQL statement.

        Each MapperProperty associated with the target mapper processes the
        statement referenced by the query context, adding columns and/or
        criterion as appropriate.
        """

        pass

    def create_row_processor(self, context, path,
                                            mapper, row, adapter):
        """Return a 3-tuple consisting of three row processing functions.

        """
        return None, None, None

    def cascade_iterator(self, type_, state, visited_instances=None,
                            halt_on=None):
        """Iterate through instances related to the given instance for
        a particular 'cascade', starting with this MapperProperty.

        Return an iterator3-tuples (instance, mapper, state).

        Note that the 'cascade' collection on this MapperProperty is
        checked first for the given type before cascade_iterator is called.

        See PropertyLoader for the related instance implementation.
        """

        return iter(())

    def set_parent(self, parent, init):
        self.parent = parent

    def instrument_class(self, mapper):  # pragma: no-coverage
        raise NotImplementedError()

    _compile_started = False
    _compile_finished = False

    def init(self):
        """Called after all mappers are created to assemble
        relationships between mappers and perform other post-mapper-creation
        initialization steps.

        """
        self._compile_started = True
        self.do_init()
        self._compile_finished = True

    @property
    def class_attribute(self):
        """Return the class-bound descriptor corresponding to this
        MapperProperty."""

        return getattr(self.parent.class_, self.key)

    def do_init(self):
        """Perform subclass-specific initialization post-mapper-creation
        steps.

        This is a template method called by the ``MapperProperty``
        object's init() method.

        """

        pass

    def post_instrument_class(self, mapper):
        """Perform instrumentation adjustments that need to occur
        after init() has completed.

        """
        pass


    def is_primary(self):
        """Return True if this ``MapperProperty``'s mapper is the
        primary mapper for its class.

        This flag is used to indicate that the ``MapperProperty`` can
        define attribute instrumentation for the class at the class
        level (as opposed to the individual instance level).
        """

        return not self.parent.non_primary

    def merge(self, session, source_state, source_dict, dest_state,
                dest_dict, load, _recursive):
        """Merge the attribute represented by this ``MapperProperty``
        from source to destination object"""

        pass

    def compare(self, operator, value, **kw):
        """Return a compare operation for the columns represented by
        this ``MapperProperty`` to the given value, which may be a
        column value or an instance.  'operator' is an operator from
        the operators module, or from sql.Comparator.

        By default uses the PropComparator attached to this MapperProperty
        under the attribute name "comparator".
        """

        return operator(self.comparator, value)

class PropComparator(operators.ColumnOperators):
    """Defines comparison operations for MapperProperty objects.

    User-defined subclasses of :class:`.PropComparator` may be created. The
    built-in Python comparison and math operator methods, such as
    ``__eq__()``, ``__lt__()``, ``__add__()``, can be overridden to provide
    new operator behavior. The custom :class:`.PropComparator` is passed to
    the mapper property via the ``comparator_factory`` argument. In each case,
    the appropriate subclass of :class:`.PropComparator` should be used::

        from sqlalchemy.orm.properties import \\
                                ColumnProperty,\\
                                CompositeProperty,\\
                                RelationshipProperty

        class MyColumnComparator(ColumnProperty.Comparator):
            pass

        class MyCompositeComparator(CompositeProperty.Comparator):
            pass

        class MyRelationshipComparator(RelationshipProperty.Comparator):
            pass

    """

    def __init__(self, prop, mapper, adapter=None):
        self.prop = self.property = prop
        self.mapper = mapper
        self.adapter = adapter

    def __clause_element__(self):
        raise NotImplementedError("%r" % self)

    def adapted(self, adapter):
        """Return a copy of this PropComparator which will use the given
        adaption function on the local side of generated expressions.

        """

        return self.__class__(self.prop, self.mapper, adapter)

    @staticmethod
    def any_op(a, b, **kwargs):
        return a.any(b, **kwargs)

    @staticmethod
    def has_op(a, b, **kwargs):
        return a.has(b, **kwargs)

    @staticmethod
    def of_type_op(a, class_):
        return a.of_type(class_)

    def of_type(self, class_):
        """Redefine this object in terms of a polymorphic subclass.

        Returns a new PropComparator from which further criterion can be
        evaluated.

        e.g.::

            query.join(Company.employees.of_type(Engineer)).\\
               filter(Engineer.name=='foo')

        :param \class_: a class or mapper indicating that criterion will be against
            this specific subclass.


        """

        return self.operate(PropComparator.of_type_op, class_)

    def any(self, criterion=None, **kwargs):
        """Return true if this collection contains any member that meets the
        given criterion.

        The usual implementation of ``any()`` is
        :meth:`.RelationshipProperty.Comparator.any`.

        :param criterion: an optional ClauseElement formulated against the
          member class' table or attributes.

        :param \**kwargs: key/value pairs corresponding to member class attribute
          names which will be compared via equality to the corresponding
          values.

        """

        return self.operate(PropComparator.any_op, criterion, **kwargs)

    def has(self, criterion=None, **kwargs):
        """Return true if this element references a member which meets the
        given criterion.

        The usual implementation of ``has()`` is
        :meth:`.RelationshipProperty.Comparator.has`.

        :param criterion: an optional ClauseElement formulated against the
          member class' table or attributes.

        :param \**kwargs: key/value pairs corresponding to member class attribute
          names which will be compared via equality to the corresponding
          values.

        """

        return self.operate(PropComparator.has_op, criterion, **kwargs)


class StrategizedProperty(MapperProperty):
    """A MapperProperty which uses selectable strategies to affect
    loading behavior.

    There is a single strategy selected by default.  Alternate
    strategies can be selected at Query time through the usage of
    ``StrategizedOption`` objects via the Query.options() method.

    """

    strategy_wildcard_key = None

    @util.memoized_property
    def _wildcard_path(self):
        if self.strategy_wildcard_key:
            return ('loaderstrategy', (self.strategy_wildcard_key,))
        else:
            return None

    def _get_context_strategy(self, context, path):
        # this is essentially performance inlining.
        key = ('loaderstrategy', path.reduced_path + (self.key,))
        cls = None
        if key in context.attributes:
            cls = context.attributes[key]
        else:
            wc_key = self._wildcard_path
            if wc_key and wc_key in context.attributes:
                cls = context.attributes[wc_key]

        if cls:
            try:
                return self._strategies[cls]
            except KeyError:
                return self.__init_strategy(cls)
        return self.strategy

    def _get_strategy(self, cls):
        try:
            return self._strategies[cls]
        except KeyError:
            return self.__init_strategy(cls)

    def __init_strategy(self, cls):
        self._strategies[cls] = strategy = cls(self)
        return strategy

    def setup(self, context, entity, path, adapter, **kwargs):
        self._get_context_strategy(context, path).\
                    setup_query(context, entity, path,
                                    adapter, **kwargs)

    def create_row_processor(self, context, path, mapper, row, adapter):
        return self._get_context_strategy(context, path).\
                    create_row_processor(context, path,
                                    mapper, row, adapter)

    def do_init(self):
        self._strategies = {}
        self.strategy = self.__init_strategy(self.strategy_class)

    def post_instrument_class(self, mapper):
        if self.is_primary() and \
            not mapper.class_manager._attr_has_impl(self.key):
            self.strategy.init_class_attribute(mapper)

class MapperOption(object):
    """Describe a modification to a Query."""

    propagate_to_loaders = False
    """if True, indicate this option should be carried along
    Query object generated by scalar or object lazy loaders.
    """

    def process_query(self, query):
        pass

    def process_query_conditionally(self, query):
        """same as process_query(), except that this option may not
        apply to the given query.

        Used when secondary loaders resend existing options to a new
        Query."""

        self.process_query(query)

class PropertyOption(MapperOption):
    """A MapperOption that is applied to a property off the mapper or
    one of its child mappers, identified by a dot-separated key
    or list of class-bound attributes. """

    def __init__(self, key, mapper=None):
        self.key = key
        self.mapper = mapper

    def process_query(self, query):
        self._process(query, True)

    def process_query_conditionally(self, query):
        self._process(query, False)

    def _process(self, query, raiseerr):
        paths = self._process_paths(query, raiseerr)
        if paths:
            self.process_query_property(query, paths)

    def process_query_property(self, query, paths):
        pass

    def __getstate__(self):
        d = self.__dict__.copy()
        d['key'] = ret = []
        for token in util.to_list(self.key):
            if isinstance(token, PropComparator):
                ret.append((token.mapper.class_, token.key))
            else:
                ret.append(token)
        return d

    def __setstate__(self, state):
        ret = []
        for key in state['key']:
            if isinstance(key, tuple):
                cls, propkey = key
                ret.append(getattr(cls, propkey))
            else:
                ret.append(key)
        state['key'] = tuple(ret)
        self.__dict__ = state

    def _find_entity_prop_comparator(self, query, token, mapper, raiseerr):
        if orm_util._is_aliased_class(mapper):
            searchfor = mapper
            isa = False
        else:
            searchfor = orm_util._class_to_mapper(mapper)
            isa = True
        for ent in query._mapper_entities:
            if ent.corresponds_to(searchfor):
                return ent
        else:
            if raiseerr:
                if not list(query._mapper_entities):
                    raise sa_exc.ArgumentError(
                        "Query has only expression-based entities - "
                        "can't find property named '%s'."
                         % (token, )
                    )
                else:
                    raise sa_exc.ArgumentError(
                        "Can't find property '%s' on any entity "
                        "specified in this Query.  Note the full path "
                        "from root (%s) to target entity must be specified."
                        % (token, ",".join(str(x) for
                            x in query._mapper_entities))
                    )
            else:
                return None

    def _find_entity_basestring(self, query, token, raiseerr):
        for ent in query._mapper_entities:
            # return only the first _MapperEntity when searching
            # based on string prop name.   Ideally object
            # attributes are used to specify more exactly.
            return ent
        else:
            if raiseerr:
                raise sa_exc.ArgumentError(
                    "Query has only expression-based entities - "
                    "can't find property named '%s'."
                     % (token, )
                )
            else:
                return None

    def _process_paths(self, query, raiseerr):
        """reconcile the 'key' for this PropertyOption with
        the current path and entities of the query.

        Return a list of affected paths.

        """
        path = orm_util.PathRegistry.root
        entity = None
        paths = []
        no_result = []

        # _current_path implies we're in a
        # secondary load with an existing path
        current_path = list(query._current_path.path)

        tokens = deque(self.key)
        while tokens:
            token = tokens.popleft()
            if isinstance(token, basestring):
                # wildcard token
                if token.endswith(':*'):
                    return [path.token(token)]
                sub_tokens = token.split(".", 1)
                token = sub_tokens[0]
                tokens.extendleft(sub_tokens[1:])

                # exhaust current_path before
                # matching tokens to entities
                if current_path:
                    if current_path[1] == token:
                        current_path = current_path[2:]
                        continue
                    else:
                        return no_result

                if not entity:
                    entity = self._find_entity_basestring(
                                        query,
                                        token,
                                        raiseerr)
                    if entity is None:
                        return no_result
                    path_element = entity.entity_zero
                    mapper = entity.mapper

                if hasattr(mapper.class_, token):
                    prop = getattr(mapper.class_, token).property
                else:
                    if raiseerr:
                        raise sa_exc.ArgumentError(
                            "Can't find property named '%s' on the "
                            "mapped entity %s in this Query. " % (
                                token, mapper)
                        )
                    else:
                        return no_result
            elif isinstance(token, PropComparator):
                prop = token.property

                # exhaust current_path before
                # matching tokens to entities
                if current_path:
                    if current_path[0:2] == \
                            [token.parententity, prop.key]:
                        current_path = current_path[2:]
                        continue
                    else:
                        return no_result

                if not entity:
                    entity = self._find_entity_prop_comparator(
                                            query,
                                            prop.key,
                                            token.parententity,
                                            raiseerr)
                    if not entity:
                        return no_result
                    path_element = entity.entity_zero
                    mapper = entity.mapper
            else:
                raise sa_exc.ArgumentError(
                        "mapper option expects "
                        "string key or list of attributes")
            assert prop is not None
            if raiseerr and not prop.parent.common_parent(mapper):
                raise sa_exc.ArgumentError("Attribute '%s' does not "
                            "link from element '%s'" % (token, path_element))

            path = path[path_element][prop.key]

            paths.append(path)

            if getattr(token, '_of_type', None):
                ac = token._of_type
                ext_info = orm_util._extended_entity_info(ac)
                path_element = mapper = ext_info.mapper
                if not ext_info.is_aliased_class:
                    ac = orm_util.with_polymorphic(
                                ext_info.mapper.base_mapper,
                                ext_info.mapper, aliased=True)
                    ext_info = orm_util._extended_entity_info(ac)
                path.set(query, "path_with_polymorphic", ext_info)
            else:
                path_element = mapper = getattr(prop, 'mapper', None)
                if mapper is None and tokens:
                    raise sa_exc.ArgumentError(
                        "Attribute '%s' of entity '%s' does not "
                        "refer to a mapped entity" %
                        (token, entity)
                    )

        if current_path:
            # ran out of tokens before
            # current_path was exhausted.
            assert not tokens
            return no_result

        return paths

class StrategizedOption(PropertyOption):
    """A MapperOption that affects which LoaderStrategy will be used
    for an operation by a StrategizedProperty.
    """

    chained = False

    def process_query_property(self, query, paths):
        strategy = self.get_strategy_class()
        if self.chained:
            for path in paths:
                path.set(
                    query,
                    "loaderstrategy",
                    strategy
                )
        else:
            paths[-1].set(
                query,
                "loaderstrategy",
                strategy
            )

    def get_strategy_class(self):
        raise NotImplementedError()

class LoaderStrategy(object):
    """Describe the loading behavior of a StrategizedProperty object.

    The ``LoaderStrategy`` interacts with the querying process in three
    ways:

    * it controls the configuration of the ``InstrumentedAttribute``
      placed on a class to handle the behavior of the attribute.  this
      may involve setting up class-level callable functions to fire
      off a select operation when the attribute is first accessed
      (i.e. a lazy load)

    * it processes the ``QueryContext`` at statement construction time,
      where it can modify the SQL statement that is being produced.
      Simple column attributes may add their represented column to the
      list of selected columns, *eager loading* properties may add
      ``LEFT OUTER JOIN`` clauses to the statement.

    * It produces "row processor" functions at result fetching time.
      These "row processor" functions populate a particular attribute
      on a particular mapped instance.

    """
    def __init__(self, parent):
        self.parent_property = parent
        self.is_class_level = False
        self.parent = self.parent_property.parent
        self.key = self.parent_property.key

    def init_class_attribute(self, mapper):
        pass

    def setup_query(self, context, entity, path, adapter, **kwargs):
        pass

    def create_row_processor(self, context, path, mapper,
                                row, adapter):
        """Return row processing functions which fulfill the contract
        specified by MapperProperty.create_row_processor.

        StrategizedProperty delegates its create_row_processor method
        directly to this method. """

        return None, None, None

    def __str__(self):
        return str(self.parent_property)


