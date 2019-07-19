from __future__ import unicode_literals

from datetime import date, datetime
from functools import partial

import pytest
from django.db.models import Q

from dj_rql.constants import (
    ComparisonOperators as CO,
    DjangoLookups,
    SearchOperators,
    RQL_EMPTY,
    RQL_NULL,
)
from dj_rql.exceptions import RQLFilterLookupError, RQLFilterParsingError, RQLFilterValueError
from tests.dj_rf.filters import BooksFilterClass
from tests.dj_rf.models import Author, Book, Page, Publisher
from tests.test_filter_cls.utils import book_qs, create_books


def filter_field(filter_name, operator, value):
    filter_cls = BooksFilterClass(book_qs)
    q = filter_cls.build_q_for_filter(filter_name, operator, str(value))
    return list(book_qs.filter(q))


def assert_filter_field_error(error_cls, filter_name, operator, value):
    with pytest.raises(error_cls) as e:
        filter_field(filter_name, operator, value)
    assert e.value.details == {
        'filter': filter_name,
        'lookup': operator,
        'value': str(value),
    }


assert_filter_field_value_error = partial(assert_filter_field_error, RQLFilterValueError)
assert_filter_field_lookup_error = partial(assert_filter_field_error, RQLFilterLookupError)


@pytest.mark.django_db
def test_id():
    filter_name = 'id'
    books = create_books()
    assert filter_field(filter_name, CO.EQ, books[0].pk) == [books[0]]
    assert filter_field(filter_name, CO.EQ, 3) == []
    assert filter_field(filter_name, CO.NE, books[1].pk) == [books[0]]
    assert filter_field(filter_name, CO.LT, books[1].pk) == [books[0]]
    assert filter_field(filter_name, CO.GE, books[0].pk) == books


@pytest.mark.django_db
def test_title():
    filter_name = 'title'
    books = [
        Book.objects.create(title='G'),
        Book.objects.create(title='R'),
        Book.objects.create(),
        Book.objects.create(title=''),
    ]
    assert filter_field(filter_name, CO.EQ, books[0].title) == [books[0]]
    assert filter_field(filter_name, CO.EQ, '"{}"'.format(books[0].title)) == [books[0]]
    assert filter_field(filter_name, CO.EQ, "'{}'".format(books[0].title)) == [books[0]]
    assert filter_field(filter_name, CO.EQ, 'N') == []
    assert filter_field(filter_name, CO.NE, books[0].title) == [books[1], books[2], books[3]]
    assert filter_field(filter_name, CO.EQ, RQL_NULL) == [books[2]]
    assert filter_field(filter_name, CO.EQ, 'NULL_ID') == [books[2]]
    assert filter_field(filter_name, CO.NE, 'NULL_ID') == [books[0], books[1], books[3]]
    assert filter_field(filter_name, CO.EQ, RQL_EMPTY) == [books[3]]
    assert filter_field(filter_name, CO.NE, RQL_EMPTY) == [books[0], books[1], books[2]]


@pytest.mark.django_db
def test_current_price():
    filter_name = 'current_price'
    books = [
        Book.objects.create(current_price=5.23),
        Book.objects.create(current_price=0.0121),
    ]
    assert filter_field(filter_name, CO.EQ, books[0].current_price) == [books[0]]
    assert filter_field(filter_name, CO.EQ, 5.2300123) == [books[0]]
    assert filter_field(filter_name, CO.EQ, 2) == []
    assert filter_field(filter_name, CO.NE, books[1].current_price) == [books[0]]
    assert filter_field(filter_name, CO.LE, books[0].current_price) == books
    assert filter_field(filter_name, CO.GT, books[1].current_price) == [books[0]]


@pytest.mark.django_db
def test_written():
    filter_name = 'written'
    books = [
        Book.objects.create(written=date(2019, 2, 12)),
        Book.objects.create(written=date(2018, 5, 5)),
    ]
    assert filter_field(filter_name, CO.EQ, '2019-02-12') == [books[0]]
    assert filter_field(filter_name, CO.EQ, '2019-05-14') == []
    assert filter_field(filter_name, CO.NE, '2019-02-12') == [books[1]]
    assert filter_field(filter_name, CO.LE, '2020-01-01') == books
    assert filter_field(filter_name, CO.GT, '2000-12-12') == books


@pytest.mark.django_db
def test_status():
    filter_name = 'status'
    books = [
        Book.objects.create(status=Book.WRITING),
        Book.objects.create(status=Book.PUBLISHED),
    ]
    assert filter_field(filter_name, CO.EQ, books[1].status) == [books[1]]
    assert filter_field(filter_name, CO.EQ, Book.PLANNING) == []
    assert filter_field(filter_name, CO.NE, books[1].status) == [books[0]]


@pytest.mark.django_db
def test_name():
    filter_name = 'name'
    authors = [
        Author.objects.create(name='Pushkin'),
        Author.objects.create(name='Lermontov'),
    ]
    books = [Book.objects.create(author=authors[index]) for index in range(2)]
    assert filter_field(filter_name, CO.EQ, authors[1].name) == [books[1]]
    assert filter_field(filter_name, CO.EQ, 'value__v') == []
    assert filter_field(filter_name, CO.NE, authors[1].name) == [books[0]]


@pytest.mark.django_db
@pytest.mark.parametrize('filter_name', ['author__email', 'author.email'])
def test_author__email(filter_name):
    authors = [
        Author.objects.create(email='email@gmail.com'),
        Author.objects.create(email='m.k@ingrammicro.com'),
    ]
    books = [Book.objects.create(author=authors[index]) for index in range(2)]
    assert filter_field(filter_name, CO.EQ, authors[1].email) == [books[1]]
    assert filter_field(filter_name, CO.EQ, 'email@example.com') == []
    assert filter_field(filter_name, CO.NE, authors[1].email) == [books[0]]


@pytest.mark.django_db
def test_author__is_male():
    filter_name = 'author.is_male'
    authors = [Author.objects.create(is_male=True) for _ in range(2)]
    books = [Book.objects.create(author=authors[index]) for index in range(2)]
    assert filter_field(filter_name, CO.EQ, 'true') == books
    assert filter_field(filter_name, CO.EQ, 'false') == []
    assert filter_field(filter_name, CO.NE, 'false') == books


@pytest.mark.django_db
def test_author__publisher__id():
    filter_name = 'author.publisher.id'
    publishers = [Publisher.objects.create() for _ in range(2)]
    authors = [Author.objects.create(publisher=publishers[index]) for index in range(2)]
    books = [Book.objects.create(author=authors[index]) for index in range(2)]
    assert filter_field(filter_name, CO.EQ, publishers[0].pk) == [books[0]]
    assert filter_field(filter_name, CO.EQ, 3) == []
    assert filter_field(filter_name, CO.NE, publishers[1].pk) == [books[0]]
    assert filter_field(filter_name, CO.LT, publishers[1].pk) == [books[0]]
    assert filter_field(filter_name, CO.GE, publishers[0].pk) == books


@pytest.mark.django_db
def test_page__number():
    filter_name = 'page.number'
    books = [Book.objects.create() for _ in range(2)]
    pages = [Page.objects.create(book=books[index], number=index) for index in range(2)]
    assert filter_field(filter_name, CO.EQ, pages[1].number) == [books[1]]
    assert filter_field(filter_name, CO.EQ, 22) == []
    assert filter_field(filter_name, CO.NE, pages[1].number) == [books[0]]


@pytest.mark.django_db
def test_page__id():
    filter_name = 'page.id'
    books = [Book.objects.create() for _ in range(2)]
    pages = [Page.objects.create(book=books[index]) for index in range(2)]
    assert filter_field(filter_name, CO.EQ, pages[1].pk) == [books[1]]
    assert filter_field(filter_name, CO.EQ, '5fde36e2-3442-4d2e-b221-a6758663dd72') == []
    assert filter_field(filter_name, CO.NE, pages[1].pk) == [books[0]]


@pytest.mark.django_db
def test_published_at():
    filter_name = 'published.at'
    books = [
        Book.objects.create(published_at=datetime(2019, 2, 12, 10, 2)),
        Book.objects.create(published_at=datetime(2018, 5, 5, 3, 4, 5)),
    ]
    assert filter_field(filter_name, CO.EQ, '2019-02-12T10:02:00') == [books[0]]
    assert filter_field(filter_name, CO.EQ, '2019-02-12T10:02Z') == [books[0]]
    assert filter_field(filter_name, CO.EQ, '2019-02-12T10:02:00+03:00') == []
    assert filter_field(filter_name, CO.NE, '2019-02-12T10:02') == [books[1]]
    assert filter_field(filter_name, CO.LE, '2020-01-01T00:00+08:00') == books
    assert filter_field(filter_name, CO.GT, '2000-12-12T00:21:00') == books


@pytest.mark.django_db
def test_rating_blog():
    filter_name = 'rating.blog'
    books = [
        Book.objects.create(blog_rating=Book.LOW_RATING),
        Book.objects.create(blog_rating=Book.HIGH_RATING),
    ]
    assert filter_field(filter_name, CO.EQ, Book.BLOG_RATING_CHOICES[0][1]) == [books[0]]
    assert filter_field(filter_name, CO.EQ, Book.BLOG_RATING_CHOICES[1][1]) == [books[1]]
    assert filter_field(filter_name, CO.NE, Book.BLOG_RATING_CHOICES[1][1]) == [books[0]]


@pytest.mark.django_db
def test_rating_blog_int():
    filter_name = 'rating.blog_int'
    books = [
        Book.objects.create(blog_rating=Book.LOW_RATING),
        Book.objects.create(blog_rating=Book.HIGH_RATING),
    ]
    assert filter_field(filter_name, CO.EQ, Book.LOW_RATING) == [books[0]]
    assert filter_field(filter_name, CO.EQ, Book.HIGH_RATING) == [books[1]]
    assert filter_field(filter_name, CO.NE, Book.HIGH_RATING) == [books[0]]


@pytest.mark.django_db
def test_amazon_rating():
    filter_name = 'amazon_rating'
    books = [
        Book.objects.create(amazon_rating=3.02),
        Book.objects.create(amazon_rating=2),
    ]
    assert filter_field(filter_name, CO.GE, 3.0200000) == [books[0]]
    assert filter_field(filter_name, CO.GE, 2.01) == [books[0]]
    assert filter_field(filter_name, CO.LT, 3.02) == [books[1]]


@pytest.mark.django_db
def test_url():
    filter_name = 'url'
    books = [
        Book.objects.create(publishing_url='http://www.site.com/'),
        Book.objects.create(publishing_url='https://example.com/'),
    ]
    assert filter_field(filter_name, CO.EQ, books[0].publishing_url) == [books[0]]
    assert filter_field(filter_name, CO.EQ, 'https://www.example.com/') == []
    assert filter_field(filter_name, CO.NE, books[1].publishing_url) == [books[0]]


@pytest.mark.django_db
def test_d_id():
    filter_name = 'd_id'
    authors = [Author.objects.create() for _ in range(2)]
    books = [
        Book.objects.create(author=authors[0]),
        Book.objects.create(author=authors[0]),
        Book.objects.create(author=authors[1]),
    ]
    assert filter_field(filter_name, CO.EQ, 3) == [books[2]]
    assert filter_field(filter_name, CO.EQ, 2) == [books[1], books[2]]
    assert filter_field(filter_name, CO.NE, 2) == [books[0]]
    assert filter_field(filter_name, CO.EQ, 1) == [books[0], books[1]]
    assert filter_field(filter_name, CO.NE, 1) == [books[2]]
    assert filter_field(filter_name, CO.EQ, 0) == []


@pytest.mark.django_db
def test_int_choice_field():
    filter_name = 'int_choice_field'
    books = [Book.objects.create(int_choice_field=choice) for choice, _ in Book.INT_CHOICES]
    assert filter_field(filter_name, CO.EQ, Book.INT_CHOICES.one) == [books[0]]
    assert filter_field(filter_name, CO.NE, Book.INT_CHOICES.two) == [books[0]]
    assert filter_field(filter_name, CO.GE, Book.INT_CHOICES.one) == books
    assert filter_field(filter_name, CO.GT, Book.INT_CHOICES.two) == []


@pytest.mark.django_db
def test_int_choice_field_repr():
    filter_name = 'int_choice_field_repr'
    books = [Book.objects.create(int_choice_field=choice) for choice, _ in Book.INT_CHOICES]
    assert filter_field(filter_name, CO.EQ, 'I') == [books[0]]
    assert filter_field(filter_name, CO.NE, 'II') == [books[0]]


@pytest.mark.django_db
def test_str_choice_field():
    filter_name = 'str_choice_field'
    books = [Book.objects.create(str_choice_field=choice) for choice, _ in Book.STR_CHOICES]
    assert filter_field(filter_name, CO.EQ, Book.STR_CHOICES.one) == [books[0]]
    assert filter_field(filter_name, CO.NE, Book.STR_CHOICES.two) == [books[0]]
    assert filter_field(filter_name, SearchOperators.I_LIKE, '*o*') == books


@pytest.mark.django_db
def test_str_choice_field_repr():
    filter_name = 'str_choice_field_repr'
    books = [Book.objects.create(str_choice_field=choice) for choice, _ in Book.STR_CHOICES]
    assert filter_field(filter_name, CO.EQ, 'I') == [books[0]]
    assert filter_field(filter_name, CO.NE, 'II') == [books[0]]


@pytest.mark.parametrize('bad_value', ['str', '2012-01-01', '2.18'])
@pytest.mark.parametrize('filter_name', ['id', 'author.publisher.id', 'page.number', 'd_id'])
def test_integer_field_fail(filter_name, bad_value):
    assert_filter_field_value_error(filter_name, CO.EQ, bad_value)


@pytest.mark.parametrize('bad_value', ['str', '2012-01-01'])
@pytest.mark.parametrize('filter_name', ['current_price', 'amazon_rating'])
def test_float_field_fail(filter_name, bad_value):
    assert_filter_field_value_error(filter_name, CO.GE, bad_value)


@pytest.mark.parametrize('bad_value', ['TRUE', '0', 'False'])
@pytest.mark.parametrize('filter_name', ['author.is_male'])
def test_boolean_field_fail(filter_name, bad_value):
    assert_filter_field_value_error(filter_name, CO.EQ, bad_value)


@pytest.mark.parametrize('bad_value', [
    '2019-02-12T10:02:00', '0', 'date', '2019:02:12', '2019-27-1',
])
@pytest.mark.parametrize('filter_name', ['written'])
def test_date_field_fail(filter_name, bad_value):
    assert_filter_field_value_error(filter_name, CO.EQ, bad_value)


@pytest.mark.parametrize('bad_value', [
    '2019-02-12', '0', 'date', '2019-02-12T27:00:00', '2019-02-12T21:00:00K',
])
@pytest.mark.parametrize('filter_name', ['published.at'])
def test_datetime_field_fail(filter_name, bad_value):
    assert_filter_field_value_error(filter_name, CO.EQ, bad_value)


@pytest.mark.parametrize('bad_operator', [CO.GT, CO.LE])
@pytest.mark.parametrize('filter_name,value', [
    ('amazon_rating', '1.23'), ('page.number', '5'),
    ('int_choice_field_repr', 'I'), ('str_choice_field_repr', 'I')
])
def test_field_lookup_fail(filter_name, value, bad_operator):
    assert_filter_field_lookup_error(filter_name, bad_operator, value)


@pytest.mark.parametrize('filter_name,bad_value', [
    ('status', 'invalid'), ('rating.blog', 'invalid'), ('rating.blog_int', '-1'),
    ('int_choice_field', 0), ('int_choice_field', 'invalid'),
    ('int_choice_field_repr', 0), ('int_choice_field_repr', 'invalid'),
    ('str_choice_field', 'zero'), ('str_choice_field_repr', 'zero'),
])
def test_bad_choice_fail(filter_name, bad_value):
    assert_filter_field_value_error(filter_name, CO.EQ, bad_value)


@pytest.mark.parametrize('bad_operator', [CO.LT, CO.GT, CO.LE, CO.LT])
@pytest.mark.parametrize('value', [RQL_NULL, RQL_EMPTY])
def test_null_empty_value_lookup_fail(bad_operator, value):
    assert_filter_field_lookup_error('title', bad_operator, value)


@pytest.mark.django_db
@pytest.mark.parametrize('operator', [CO.EQ, CO.NE, CO.GT])
@pytest.mark.parametrize('filter_name', ['invalid'])
def test_ignored_filters(filter_name, operator):
    books = create_books()
    assert filter_field(filter_name, operator, 'value') == books


@pytest.mark.parametrize('filter_name', ['id', 'page.number', 'author.is_male', 'name'])
def test_empty_value_fail(filter_name):
    assert_filter_field_value_error(filter_name, CO.EQ, RQL_EMPTY)


@pytest.mark.parametrize('value,db_lookup,db_value', [
    ('value', DjangoLookups.EXACT, 'value'),
    ('*value', DjangoLookups.ENDSWITH, 'value'),
    ('value*', DjangoLookups.STARTSWITH, 'value'),
    ('*value*', DjangoLookups.CONTAINS, 'value'),
    ('val*ue', DjangoLookups.REGEX, '^val(.*?)ue$'),
    ('val*ue*', DjangoLookups.REGEX, '^val(.*?)ue'),
    ('*val*ue', DjangoLookups.REGEX, 'val(.*?)ue$'),
    ('*val*ue*', DjangoLookups.REGEX, 'val(.*?)ue'),
    ('*', DjangoLookups.REGEX, '(.*?)'),
])
def test_searching_q_ok(value, db_lookup, db_value):
    cls = BooksFilterClass(book_qs)

    for v in (value, '"{}"'.format(value)):
        like_q = cls.build_q_for_filter('title', SearchOperators.LIKE, v)
        assert like_q.children[0] == ('title__{}'.format(db_lookup), db_value)

    i_like_q = cls.build_q_for_filter('title', SearchOperators.I_LIKE, value)
    assert i_like_q.children[0] == ('title__i{}'.format(db_lookup), db_value)


@pytest.mark.django_db
def test_searching_db_ok():
    filter_name = 'title'
    title = 'Long title'
    book = Book.objects.create(title=title)
    assert filter_field(filter_name, SearchOperators.I_LIKE, title.upper()) == [book]
    assert filter_field(filter_name, SearchOperators.LIKE, 'title') == []
    assert filter_field(filter_name, SearchOperators.LIKE, 'L*') == [book]
    assert filter_field(filter_name, SearchOperators.I_LIKE, '*E') == [book]
    assert filter_field(filter_name, SearchOperators.LIKE, '*ng*') == [book]
    assert filter_field(filter_name, SearchOperators.LIKE, '*ng*') == [book]
    assert filter_field(filter_name, SearchOperators.LIKE, '*t*t*') == [book]
    assert filter_field(filter_name, SearchOperators.LIKE, '*t*le') == [book]
    assert filter_field(filter_name, SearchOperators.I_LIKE, 'lo*g*') == [book]
    assert filter_field(filter_name, SearchOperators.LIKE, 't*le') == []
    assert filter_field(filter_name, SearchOperators.LIKE, '*') == [book]


@pytest.mark.parametrize('bad_value', ['value**value', '**v'])
@pytest.mark.parametrize('operator', [SearchOperators.LIKE, SearchOperators.I_LIKE])
def test_searching_value_fail(bad_value, operator):
    assert_filter_field_value_error('title', operator, bad_value)


@pytest.mark.django_db
def test_custom_filter_ok():
    class CustomCls(BooksFilterClass):
        def build_q_for_custom_filter(self, filter_name, operator, str_value):
            return Q(id__gte=2)

    filter_cls = CustomCls(book_qs)
    q = filter_cls.build_q_for_filter('custom_filter', SearchOperators.I_LIKE, 'value')

    books = [Book.objects.create() for _ in range(2)]
    assert list(book_qs.filter(q)) == [books[1]]


def test_custom_filter_fail():
    with pytest.raises(RQLFilterParsingError) as e:
        filter_field('custom_filter', SearchOperators.I_LIKE, 'value')
    assert e.value.details['error'] == 'Filter logic is not implemented: custom_filter.'