import beaker
import pyteal as pt
from algokit_utils import DELETABLE_TEMPLATE_NAME, UPDATABLE_TEMPLATE_NAME


class DaoState:
    # INSERT YOUR CODE HERE
    ...


app = beaker.Application("dao", state=DaoState())


@app.update(authorize=beaker.Authorize.only_creator(), bare=True)
def update() -> pt.Expr:
    return pt.Assert(
        pt.Tmpl.Int(UPDATABLE_TEMPLATE_NAME),
        comment="Check app is updatable",
    )


@app.delete(authorize=beaker.Authorize.only_creator(), bare=True)
def delete() -> pt.Expr:
    return pt.Assert(
        pt.Tmpl.Int(DELETABLE_TEMPLATE_NAME),
        comment="Check app is deletable",
    )


@app.create
def create(proposal: pt.abi.String, end_voting: pt.abi.Uint64) -> pt.Expr:
    # INSERT YOUR CODE HERE
    ...


@app.external(authorize=beaker.Authorize.only_creator())
def bootstrap(*, output: pt.abi.Uint64) -> pt.Expr:
    # INSERT YOUR CODE HERE
    ...


@app.opt_in
def register(registered_asa: pt.abi.Asset) -> pt.Expr:
    # INSERT YOUR CODE HERE
    ...


@app.close_out
def deregister(registered_asa: pt.abi.Asset) -> pt.Expr:
    # INSERT YOUR CODE HERE
    ...


@app.clear_state
def clear_state() -> pt.Expr:
    # INSERT YOUR CODE HERE
    ...


@app.external
def vote(in_favor: pt.abi.Bool) -> pt.Expr:
    # INSERT YOUR CODE HERE
    ...


@app.external(read_only=True)
def get_proposal(*, output: pt.abi.String) -> pt.Expr:
    # INSERT YOUR CODE HERE
    ...


@app.external(read_only=True)
def get_registered_asa(*, output: pt.abi.Uint64) -> pt.Expr:
    # INSERT YOUR CODE HERE
    ...


class GetVotesReturn(pt.abi.NamedTuple):
    # INSERT YOUR CODE HERE
    ...


@app.external(read_only=True)
def get_votes(*, output: GetVotesReturn) -> pt.Expr:
    # INSERT YOUR CODE HERE
    ...
