
import argparse
from typing import TYPE_CHECKING
from peakrdl.plugins.exporter import ExporterSubcommandPlugin #pylint: disable-import-error
from peakrdl.config import schema
from systemrdl.node import AddrmapNode #pylint: disable-import-error
from .pss_exporter import PssExporter

class Exporter(ExporterSubcommandPlugin):
    short_desc = "Create a PSS register package of an address space"

    cfg_schema = {
#        "std": schema.Choice(list())
    }

    def add_exporter_arguments(self, arg_group: argparse._ActionsContainer) -> None:
        arg_group.add_argument(
            "-p", "--package",
            type=str,
            default="",
            help="""
            Specifies the name of the PSS package in which to place the registers
            """
        )

    def do_export(self, top_node: AddrmapNode, options: argparse.Namespace) -> None:
        exporter = PssExporter()
        exporter.export(
            top_node,
            path=options.output,
            package=options.package
        )
