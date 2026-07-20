"""Registro de fuentes. Cada módulo expone fetch(profile) -> list[Job]."""
from . import web3career, cryptojobslist, remote3, linkedin, remoteok

REGISTRY = {
    "web3career": web3career,
    "cryptojobslist": cryptojobslist,
    "remote3": remote3,
    "linkedin": linkedin,
    "remoteok": remoteok,
}
