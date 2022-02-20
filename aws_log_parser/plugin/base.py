import concurrent.futures
import logging
import pprint
import typing

from dataclasses import dataclass, field

from ..util import batcher

logger = logging.getLogger(__name__)


@dataclass
class AwsLogParserPlugin:
    """
    Resolve the instance_id from its private ip address.
    """

    batch_size: typing.Optional[int] = None
    max_workers: typing.Optional[int] = None

    # Overriden
    produced_attr: typing.Optional[str] = None
    consumed_attr: typing.Optional[str] = None

    # Internal
    _results: typing.Dict[str, typing.Optional[str]] = field(default_factory=dict)

    def run(self, values):
        unknown = values - self._results.keys()
        logger.debug(f"{self.produced_attr} {pprint.pformat(unknown)}")

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:

            futures = (
                {
                    executor.submit(self.query, batch)
                    for batch in batcher(unknown, self.batch_size)
                }
                if self.batch_size
                else {executor.submit(self.query, value) for value in unknown}
            )

            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                except Exception as exc:
                    logger.error(str(exc), exc_info=True)
                else:
                    if result:
                        self._results.update(result)

    def query(self, _):
        raise NotImplementedError

    def augment(self, log_entry):
        if self.consumed_attr and self.produced_attr:
            consumed_value = getattr(log_entry, self.consumed_attr)
            produced_value = self._results.get(consumed_value)
            setattr(
                log_entry,
                self.produced_attr,
                produced_value,
            )