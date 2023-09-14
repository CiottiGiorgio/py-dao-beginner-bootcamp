import beaker
import pyteal as pt
from algokit_utils import DELETABLE_TEMPLATE_NAME, UPDATABLE_TEMPLATE_NAME


class DaoState:
    registered_asa_id = beaker.GlobalStateValue(pt.TealType.uint64)
    proposal = beaker.GlobalStateValue(pt.TealType.bytes)
    votes_total = beaker.GlobalStateValue(pt.TealType.uint64)
    votes_in_favor = beaker.GlobalStateValue(pt.TealType.uint64)

    has_voted = beaker.LocalStateValue(pt.TealType.uint64)


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


@app.external(authorize=beaker.Authorize.only_creator())
def bootstrap(*, output: pt.abi.Uint64) -> pt.Expr:
    return pt.Seq(
        pt.Assert(pt.Not(app.state.registered_asa_id.exists())),
        pt.InnerTxnBuilder.Begin(),
        pt.InnerTxnBuilder.SetFields(
            {
                pt.TxnField.type_enum: pt.TxnType.AssetConfig,
                pt.TxnField.config_asset_total: pt.Int(1_000),
                pt.TxnField.config_asset_decimals: pt.Int(0),
                pt.TxnField.config_asset_default_frozen: pt.Int(0),
                pt.TxnField.config_asset_freeze: pt.Global.current_application_address(),
                pt.TxnField.fee: pt.Int(0),
            }
        ),
        pt.InnerTxnBuilder.Submit(),
        app.state.registered_asa_id.set(pt.InnerTxn.created_asset_id()),
        output.set(pt.InnerTxn.created_asset_id()),
    )


@app.opt_in
def register(registered_asa: pt.abi.Asset) -> pt.Expr:
    return pt.Seq(
        (
            asa_balance := pt.AssetHolding.balance(
                pt.Txn.sender(), app.state.registered_asa_id.get()
            )
        ),
        pt.Assert(asa_balance.hasValue()),
        pt.Assert(asa_balance.value() == pt.Int(0)),
        app.state.has_voted.set(pt.Int(0)),
        pt.InnerTxnBuilder.Begin(),
        pt.InnerTxnBuilder.SetFields(
            {
                pt.TxnField.type_enum: pt.TxnType.AssetTransfer,
                pt.TxnField.xfer_asset: app.state.registered_asa_id.get(),
                pt.TxnField.asset_receiver: pt.Txn.sender(),
                pt.TxnField.asset_amount: pt.Int(1),
                pt.TxnField.fee: pt.Int(0),
            }
        ),
        pt.InnerTxnBuilder.Next(),
        pt.InnerTxnBuilder.SetFields(
            {
                pt.TxnField.type_enum: pt.TxnType.AssetFreeze,
                pt.TxnField.freeze_asset: app.state.registered_asa_id.get(),
                pt.TxnField.freeze_asset_account: pt.Txn.sender(),
                pt.TxnField.freeze_asset_frozen: pt.Int(1),
                pt.TxnField.fee: pt.Int(0),
            }
        ),
        pt.InnerTxnBuilder.Submit(),
    )


@app.external
def vote(in_favor: pt.abi.Bool, registered_asa: pt.abi.Asset) -> pt.Expr:
    return pt.Seq(
        (
            asa_balance := pt.AssetHolding.balance(
                pt.Txn.sender(), app.state.registered_asa_id.get()
            )
        ),
        pt.Assert(asa_balance.hasValue()),
        pt.Assert(asa_balance.value() == pt.Int(1)),
        pt.Assert(app.state.has_voted.get() == pt.Int(0)),
        app.state.has_voted.set(pt.Int(1)),
        app.state.votes_total.set(app.state.votes_total.get() + pt.Int(1)),
        pt.If(in_favor.get()).Then(
            app.state.votes_in_favor.set(app.state.votes_in_favor.get() + pt.Int(1))
        ),
    )


@app.external(read_only=True)
def get_proposal(*, output: pt.abi.String) -> pt.Expr:
    return output.set(app.state.proposal.get())


@app.external(read_only=True)
def get_registered_asa(*, output: pt.abi.Uint64) -> pt.Expr:
    return pt.Seq(
        pt.Assert(app.state.registered_asa_id.exists()),
        output.set(app.state.registered_asa_id.get()),
    )


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
