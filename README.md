Django RQL
==========

`django-rql` is an Django application, that implements RQL filter backend for your web application.


RQL
---

RQL (Resource query language) is designed for modern application development. It is built for the web, ready for NoSQL, and highly extensible with simple syntax. 
This is a query language fast and convenient database interaction. RQL was designed for use in URLs to request object-style data structures.


[RQL for Web](https://www.sitepen.com/blog/resource-query-language-a-query-language-for-the-web-nosql/)
[RQL Reference](https://docs.cloudblue.com/oa/8.0/sdk/api/rest/rql/index.html)

Notes
-----

Parsing is done with [Lark](https://github.com/lark-parser/lark) ([cheatsheet](https://lark-parser.readthedocs.io/en/latest/lark_cheatsheet.pdf)).
The current parsing algorithm is [LALR(1)](https://www.wikiwand.com/en/LALR_parser) with standard lexer.

Currently supported operators
=============================
1. Comparison (eq, ne, gt, ge, lt, le, like, ilike, search)
0. List (in, out)
0. Logical (and, or, not)
0. Constants (null(), empty()) 
0. Ordering (ordering)


Example
=======
```python
from dj_rql.constants import FilterLookups
from dj_rql.filter_cls import RQLFilterClass, RQL_NULL


class ModelFilterClass(RQLFilterClass):
    """
    MODEL - Django ORM model
    FILTERS - List of filters
    EXTENDED_SEARCH_ORM_ROUTES - List of additional Django ORM fields for search
    
    Filters can be set in two ways:
        1) string (default settings are calculated from ORM)
        2) dict (overriding settings for specific cases)
        
    Filter Dict Structure
    {
        'filter': str
        # or
        'namespace': str
        
        'source': str
        # or
        'sources': iterable
        # or
        'custom': bool
        
        'use_repr': bool  # can't be used in namespaces
        'ordering': bool  # can't be true if 'use_repr=True'
        'search': bool    # can't be true if 'use_repr=True'
    }
    
    """
    MODEL = Model
    FILTERS = ['id', {
        # `null_values` can be set to override ORM is_null behaviour
        # RQL_NULL is the default value if NULL lookup is supported by field
        'filter': 'title',
        'null_values': {RQL_NULL, 'NULL_ID'},
        'ordering': False,
    }, {
        # `ordering` can be set to True, if filter must support ordering (sorting)
        # `ordering` can't be applied to non-db fields
        'filter': 'status',
        'ordering': True,
    }, {
        # `search` must be set to True for filter to be used in searching
        # `search` must be applied only to text db-fields, which have ilike lookup
        'filter': 'author__email',
        'search': True,
    }, {
        # `source` must be set when filter name doesn't match ORM path
        'filter': 'name',
        'source': 'author__name',
    }, {
        # `namespace` is useful for API consistency, when dealing with related models
        'namespace': 'author',
        'filters': ['id', 'name'],  # will be converted to `author.id` and `author.name`
    },{
        'filter': 'published.at',
        'source': 'published_at',
    }, {
        # `use_repr` flag is used to filter by choice representations
        'filter': 'rating.blog',
        'source': 'blog_rating',
        'use_repr': True,
    }, {
        'filter': 'rating.blog_int',
        'source': 'blog_rating',
        'use_repr': False,
        'ordering': True,
    }, {
        # We can change default lookups for a certain filter
        'filter': 'amazon_rating',
        'lookups': {FilterLookups.GE, FilterLookups.LT},
    }, {
        # Sometimes it's needed to filter by several sources at once (distinct is always True).
        # F.e. this could be helpful for searching.
        'filter': 'd_id',
        'sources': {'id', 'author__id'},
        'ordering': True,
    }, {
        # Some fields may have no DB representation or non-typical ORM filtering
        # `custom` option must be set to True for such fields
        'filter': 'custom_filter',
        'custom': True,
        'lookups': {FilterLookups.EQ, FilterLookups.IN, FilterLookups.I_LIKE},
        'ordering': True,
        'search': True,
        
        'custom_data': [1],
    }]


from dj_rql.drf import RQLContentRangeLimitOffsetPagination, RQLFilterBackend

class DRFViewSet(mixins.ListModelMixin, GenericViewSet):
    queryset = MODEL.objects.all()
    serializer_class = ModelSerializer
    rql_filter_class = ModelFilterClass
    pagination_class = RQLContentRangeLimitOffsetPagination
    filter_backends = (RQLFilterBackend,)
```

Notes
=====
0. Values with whitespaces or special characters, like ',' need to have “” or ‘’
1. Supported date format is ISO8601: 2019-02-12
2. Supported datetime format is ISO8601: 2019-02-12T10:02:00 / 2019-02-12T10:02Z / 2019-02-12T10:02:00+03:00


Django Rest Framework Extensions
================================
1. Pagination (limit, offset)
0. Support for Choices() fields from [Django Model Utilities](https://django-model-utils.readthedocs.io/en/latest/utilities.html#choices)
0. Support for custom fields, inherited at any depth from basic model fields, like CharField().
0. Backend `DjangoFiltersRQLFilterBackend` with automatic conversion of [Django-Filters](https://django-filter.readthedocs.io/en/master/) query to RQL query.

Best Practices
==============
1. Use `dj_rql.utils.assert_filter_cls` to test your API view filters. If the mappings are correct and there is no custom filtering logic, then it's practically guaranteed, that filtering will work correctly.
0. Prefer using `custom=True` with `RQLFilterClass.build_q_for_custom_filter` overriding over overriding `RQLFilterClass.build_q_for_filter`.
0. Custom filters may support ordering (`ordering=True`) with `build_name_for_custom_ordering`.

Development
===========

1. Python 2.7+
0. Install dependencies `requirements/dev.txt`

Testing
=======

1. Python 2.7+
0. Install dependencies `requirements/test.txt`
0. `export PYTHONPATH=/your/path/to/django-rql/`

Check code style: `flake8`
Run tests: `pytest`

Tests reports are generated in `tests/reports`. 
* `out.xml` - JUnit test results
* `coverage.xml` - Coverage xml results

To generate HTML coverage reports use:
`--cov-report html:tests/reports/cov_html`
