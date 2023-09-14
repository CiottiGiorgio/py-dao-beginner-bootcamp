import beaker
import pyteal as pt
from algokit_utils import DELETABLE_TEMPLATE_NAME, UPDATABLE_TEMPLATE_NAME


class DaoState:
    proposal = beaker.GlobalStateValue(pt.TealType.bytes)
    votes_total = beaker.GlobalStateValue(pt.TealType.uint64)
    votes_in_favor = beaker.GlobalStateValue(pt.TealType.uint64)


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
def create(proposal: pt.abi.String) -> pt.Expr:
    return app.state.proposal.set(proposal.get())


@app.external
def vote(in_favor: pt.abi.Bool) -> pt.Expr:
    return pt.Seq(
        app.state.votes_total.set(app.state.votes_total.get() + pt.Int(1)),
        pt.If(in_favor.get()).Then(
            app.state.votes_in_favor.set(app.state.votes_in_favor.get() + pt.Int(1))
        ),
    )


@app.external(read_only=True)
def get_proposal(*, output: pt.abi.String) -> pt.Expr:
    return output.set(app.state.proposal.get())


class GetVotesReturn(pt.abi.NamedTuple):
    total: pt.abi.Field[pt.abi.Uint64]
    in_favor: pt.abi.Field[pt.abi.Uint64]


@app.external(read_only=True)
def get_votes(*, output: GetVotesReturn) -> pt.Expr:
    total = pt.abi.Uint64()
    in_favor = pt.abi.Uint64()

    return pt.Seq(
        pt.Assert(app.state.votes_total.exists()),
        total.set(app.state.votes_total.get()),
        in_favor.set(app.state.votes_in_favor.get()),
        output.set(total, in_favor),
    )
