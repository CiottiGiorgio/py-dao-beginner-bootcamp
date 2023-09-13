import beaker
import pyteal as pt
from algokit_utils import DELETABLE_TEMPLATE_NAME, UPDATABLE_TEMPLATE_NAME


class DaoState:
    proposal = beaker.GlobalStateValue(pt.TealType.bytes)


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


@app.external(read_only=True)
def get_proposal(*, output: pt.abi.String) -> pt.Expr:
    return output.set(app.state.proposal.get())
