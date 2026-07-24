from collections.abc import Iterable
from dataclasses import dataclass

from .cyclotomic import (
    build_binary_cyclotomic_coset,
    canonicalize_binary_cyclotomic_coset,
)

from .field import (
    GF2m,
    create_gf2m,
)

from .polynomial import (
    coefficients_to_integer,
    gf2_polynomial_degree,
    gf2_polynomial_mod,
    gf2_polynomial_multiply,
)


def trim_extension_field_polynomial(
    coefficients: Iterable[int],
) -> list[int]:
    """
    Удаляет старшие нулевые коэффициенты полинома.

    Коэффициенты хранятся от младшей степени к старшей:

        [a0, a1, a2]

    соответствует:

        a0 + a1*x + a2*x^2
    """
    result = list(coefficients)

    if not result:
        return [0]

    while len(result) > 1 and result[-1] == 0:
        result.pop()

    return result


def multiply_extension_field_polynomials(
    left: Iterable[int],
    right: Iterable[int],
    field: GF2m,
) -> list[int]:
    """
    Перемножает два полинома, коэффициенты которых
    принадлежат GF(2^m).

    Коэффициенты располагаются от младшей степени
    к старшей.
    """
    left_coefficients = list(left)
    right_coefficients = list(right)

    if not left_coefficients:
        raise ValueError(
            "Полином left не должен быть пустым"
        )

    if not right_coefficients:
        raise ValueError(
            "Полином right не должен быть пустым"
        )

    for coefficient in left_coefficients:
        field.validate_element(
            coefficient,
            name="left coefficient",
        )

    for coefficient in right_coefficients:
        field.validate_element(
            coefficient,
            name="right coefficient",
        )

    result_length = (
        len(left_coefficients)
        + len(right_coefficients)
        - 1
    )

    result = [0] * result_length

    for left_degree, left_coefficient in enumerate(
        left_coefficients
    ):
        for right_degree, right_coefficient in enumerate(
            right_coefficients
        ):
            product = field.multiply(
                left_coefficient,
                right_coefficient,
            )

            result_degree = left_degree + right_degree

            result[result_degree] = field.add(
                result[result_degree],
                product,
            )

    return trim_extension_field_polynomial(result)


def evaluate_extension_field_polynomial(
    coefficients: Iterable[int],
    value: int,
    field: GF2m,
) -> int:
    """
    Вычисляет значение полинома над GF(2^m)
    методом Горнера.

    Коэффициенты передаются от младшей степени
    к старшей.
    """
    polynomial = trim_extension_field_polynomial(
        coefficients
    )

    value = field.validate_element(
        value,
        name="value",
    )

    result = 0

    for coefficient in reversed(polynomial):
        coefficient = field.validate_element(
            coefficient,
            name="coefficient",
        )

        result = field.multiply(result, value)
        result = field.add(result, coefficient)

    return result


def evaluate_binary_polynomial_in_field(
    polynomial: int,
    value: int,
    field: GF2m,
) -> int:
    """
    Вычисляет значение двоичного полинома
    в точке поля GF(2^m).

    Коэффициенты полинома равны только 0 или 1,
    но точка value является элементом GF(2^m).
    """
    if not isinstance(polynomial, int):
        raise TypeError(
            "polynomial должен быть целым числом"
        )

    if polynomial < 0:
        raise ValueError(
            "polynomial не может быть отрицательным"
        )

    value = field.validate_element(
        value,
        name="value",
    )

    if polynomial == 0:
        return 0

    degree = gf2_polynomial_degree(polynomial)
    result = 0

    for current_degree in range(degree, -1, -1):
        result = field.multiply(result, value)

        coefficient = (
            polynomial >> current_degree
        ) & 1

        if coefficient == 1:
            result = field.add(result, 1)

    return result


def build_minimal_polynomial(
    cyclotomic_coset: Iterable[int],
    field: GF2m,
) -> int:
    """
    Строит минимальный полином для циклотомического класса.

    Для класса:

        C_i = {i, 2i, 4i, ...}

    минимальный полином имеет вид:

        M_i(x) = product(
            x + alpha^j
            for j in C_i
        )

    В характеристике 2:

        x - alpha^j = x + alpha^j

    После перемножения коэффициенты минимального полинома
    должны принадлежать базовому полю GF(2), то есть быть 0 или 1.
    """
    exponents = tuple(cyclotomic_coset)

    if not exponents:
        raise ValueError(
            "Циклотомический класс не должен быть пустым"
        )

    polynomial = [1]

    for exponent in exponents:
        root = field.alpha(exponent)

        # x + root:
        #
        # коэффициент при x^0 = root
        # коэффициент при x^1 = 1
        factor = [root, 1]

        polynomial = multiply_extension_field_polynomials(
            left=polynomial,
            right=factor,
            field=field,
        )

    non_binary_coefficients = [
        coefficient
        for coefficient in polynomial
        if coefficient not in (0, 1)
    ]

    if non_binary_coefficients:
        raise ValueError(
            "Минимальный полином построен некорректно: "
            "его коэффициенты не принадлежат GF(2). "
            f"Коэффициенты: {polynomial}"
        )

    minimal_polynomial = coefficients_to_integer(
        polynomial
    )

    for exponent in exponents:
        root = field.alpha(exponent)

        value = evaluate_binary_polynomial_in_field(
            polynomial=minimal_polynomial,
            value=root,
            field=field,
        )

        if value != 0:
            raise ValueError(
                "Минимальный полином не обращается в ноль "
                f"на корне alpha^{exponent}"
            )

    return minimal_polynomial


@dataclass(frozen=True)
class BCHGeneratorResult:
    """
    Результат построения порождающего полинома
    примитивного бинарного BCH-кода.
    """

    m: int
    n: int
    k: int

    designed_distance: int
    guaranteed_error_correction: int
    first_root: int

    primitive_polynomial: int

    root_exponents: tuple[int, ...]

    cyclotomic_cosets: tuple[
        tuple[int, ...],
        ...
    ]

    minimal_polynomials: tuple[int, ...]

    generator_polynomial: int

    @property
    def generator_degree(self) -> int:
        """
        Степень порождающего полинома:

            deg(g) = n - k
        """
        return gf2_polynomial_degree(
            self.generator_polynomial
        )


def build_bch_generator_polynomial(
    m: int,
    designed_distance: int,
    primitive_polynomial: int | None = None,
    first_root: int = 1,
) -> BCHGeneratorResult:
    """
    Строит порождающий полином примитивного бинарного BCH-кода.

    Для примитивного кода:

        n = 2^m - 1

    Для узкого BCH-кода first_root = 1.

    Требуемые корни:

        alpha^first_root,
        alpha^(first_root + 1),
        ...
        alpha^(first_root + designed_distance - 2)

    Порождающий полином является произведением различных
    минимальных полиномов этих корней.
    """
    field = create_gf2m(
        m=m,
        primitive_polynomial=primitive_polynomial,
    )

    n = field.order

    if not isinstance(designed_distance, int):
        raise TypeError(
            "designed_distance должно быть целым числом"
        )

    if designed_distance < 2:
        raise ValueError(
            "designed_distance должно быть не меньше 2"
        )

    if designed_distance > n:
        raise ValueError(
            "designed_distance не может быть больше "
            f"длины кода n = {n}"
        )

    if not isinstance(first_root, int):
        raise TypeError(
            "first_root должен быть целым числом"
        )

    root_exponents = tuple(
        (first_root + offset) % n
        for offset in range(designed_distance - 1)
    )

    selected_cosets: list[tuple[int, ...]] = []
    seen_cosets: set[tuple[int, ...]] = set()

    for exponent in root_exponents:
        coset = build_binary_cyclotomic_coset(
            exponent=exponent,
            code_length=n,
        )

        canonical_coset = (
            canonicalize_binary_cyclotomic_coset(coset)
        )

        if canonical_coset in seen_cosets:
            continue

        seen_cosets.add(canonical_coset)
        selected_cosets.append(coset)

    minimal_polynomials: list[int] = []
    generator_polynomial = 1

    for coset in selected_cosets:
        minimal_polynomial = build_minimal_polynomial(
            cyclotomic_coset=coset,
            field=field,
        )

        minimal_polynomials.append(
            minimal_polynomial
        )

        generator_polynomial = (
            gf2_polynomial_multiply(
                generator_polynomial,
                minimal_polynomial,
            )
        )

    generator_degree = gf2_polynomial_degree(
        generator_polynomial
    )

    k = n - generator_degree

    if k <= 0:
        raise ValueError(
            "Получена неположительная размерность BCH-кода: "
            f"n = {n}, deg(g) = {generator_degree}, k = {k}"
        )

    # Для циклического кода g(x) должен делить x^n + 1.
    # В GF(2) полиномы x^n - 1 и x^n + 1 совпадают.
    x_n_plus_one = (1 << n) | 1

    remainder = gf2_polynomial_mod(
        dividend=x_n_plus_one,
        divisor=generator_polynomial,
    )

    if remainder != 0:
        raise ValueError(
            "Порождающий полином BCH построен некорректно: "
            "он не делит x^n + 1"
        )

    # Дополнительно проверяем все требуемые корни.
    for exponent in root_exponents:
        root = field.alpha(exponent)

        value = evaluate_binary_polynomial_in_field(
            polynomial=generator_polynomial,
            value=root,
            field=field,
        )

        if value != 0:
            raise ValueError(
                "Порождающий полином не имеет требуемого корня "
                f"alpha^{exponent}"
            )

    guaranteed_error_correction = (
        designed_distance - 1
    ) // 2

    return BCHGeneratorResult(
        m=m,
        n=n,
        k=k,
        designed_distance=designed_distance,
        guaranteed_error_correction=(
            guaranteed_error_correction
        ),
        first_root=first_root % n,
        primitive_polynomial=field.primitive_polynomial,
        root_exponents=root_exponents,
        cyclotomic_cosets=tuple(selected_cosets),
        minimal_polynomials=tuple(
            minimal_polynomials
        ),
        generator_polynomial=generator_polynomial,
    )