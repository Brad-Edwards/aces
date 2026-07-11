"""Versioned SDL source-profile policy and YAML 1.2 Core resolver setup."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

import yaml
from yaml.nodes import ScalarNode

SDL_SOURCE_FORMAT = "sdl-yaml/v1"
SDL_CANONICAL_PROFILE = "aces-sdl-semantic/v1"


class SDLMigrationPolicy(str, Enum):
    """Treatment of recognized non-canonical SDL source spellings."""

    REJECT = "reject"
    ACCEPT = "accept"


@dataclass(frozen=True)
class SDLParserLimits:
    """Operational work limits for one SDL YAML source document."""

    max_input_bytes: int = 8 * 1024 * 1024
    max_scalar_bytes: int = 1024 * 1024
    max_depth: int = 128
    max_nodes: int = 100_000
    max_aliases: int = 256
    max_expanded_nodes: int = 250_000

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")


DEFAULT_PARSER_LIMITS = SDLParserLimits()

_BOOL_RE = re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$")
_FLOAT_RE = re.compile(
    r"""^(?:
        [-+]?(?:
            \.[0-9]+(?:[eE][-+]?[0-9]+)?
          | [0-9]+(?:\.[0-9]*)?(?:[eE][-+]?[0-9]+)
          | [0-9]+\.[0-9]*
        )
      | [-+]?\.(?:inf|Inf|INF)
      | \.(?:nan|NaN|NAN)
    )$""",
    re.X,
)
_INT_RE = re.compile(r"^(?:[-+]?[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+)$")
_MERGE_RE = re.compile(r"^(?:<<)$")
_NULL_RE = re.compile(r"^(?:~|null|Null|NULL|)$")


def install_yaml_12_core_resolvers(loader_cls: type[yaml.SafeLoader]) -> None:
    """Install SDL's private YAML 1.2 Core resolver table on ``loader_cls``."""

    loader_cls.yaml_implicit_resolvers = {}
    loader_cls.add_implicit_resolver("tag:yaml.org,2002:bool", _BOOL_RE, list("tTfF"))
    loader_cls.add_implicit_resolver("tag:yaml.org,2002:float", _FLOAT_RE, list("-+0123456789."))
    loader_cls.add_implicit_resolver("tag:yaml.org,2002:int", _INT_RE, list("-+0123456789"))
    loader_cls.add_implicit_resolver("tag:yaml.org,2002:merge", _MERGE_RE, ["<"])
    loader_cls.add_implicit_resolver("tag:yaml.org,2002:null", _NULL_RE, ["~", "n", "N", ""])
    loader_cls.add_constructor("tag:yaml.org,2002:int", _construct_core_int)


def _construct_core_int(loader: yaml.SafeLoader, node: ScalarNode) -> int:
    value = loader.construct_scalar(node).replace("_", "")
    sign = -1 if value.startswith("-") else 1
    unsigned = value[1:] if value[:1] in {"-", "+"} else value
    if unsigned.startswith("0o"):
        return sign * int(unsigned[2:], 8)
    if unsigned.startswith("0x"):
        return sign * int(unsigned[2:], 16)
    return sign * int(unsigned, 10)
