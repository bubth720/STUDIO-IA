import pytest
from collect_binary_licenses import package_owner


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("libexpat1:amd64: /usr/lib/x86_64-linux-gnu/libexpat.so.1\n", "libexpat1:amd64"),
        (
            "fonts-dejavu-core: /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf\n",
            "fonts-dejavu-core",
        ),
        (
            "diversion by libreadline8t64 from: /lib/x86_64-linux-gnu/libreadline.so.8\n"
            "diversion by libreadline8t64 to: "
            "/lib/x86_64-linux-gnu/libreadline.so.8.usr-is-merged\n"
            "libreadline8t64:amd64: /lib/x86_64-linux-gnu/libreadline.so.8\n",
            "libreadline8t64:amd64",
        ),
        (
            "diversion by libreadline8t64 from: /lib/x86_64-linux-gnu/libreadline.so.8\n"
            "diversion by libreadline8t64 to: "
            "/lib/x86_64-linux-gnu/libreadline.so.8.usr-is-merged\n",
            None,
        ),
        (
            "détournement par libreadline8t64 depuis : /lib/x86_64-linux-gnu/libreadline.so.8\n"
            "libreadline8t64:amd64: /usr/lib/x86_64-linux-gnu/libreadline.so.8\n",
            "libreadline8t64:amd64",
        ),
        ("No package ownership found\n", None),
    ],
)
def test_dpkg_owner_excludes_diversion_annotations(output, expected):
    assert package_owner(output) == expected
