import numpy as np
from contextlib import contextmanager
from matplotlib import image as mpimg
from matplotlib import pyplot as plt
from matplotlib import gridspec
from gcbmanimation.plot.resultsplot import ResultsPlot
from gcbmanimation.animator.frame import Frame
from gcbmanimation.util.tempfile import TempFileManager

class BasicResultsPlot(ResultsPlot):

    def __init__(self, title, provider, units):
        self._title = title
        self._provider = provider
        self._units = units

    def render(self, start_year=None, end_year=None, **kwargs):
        '''
        Renders the configured plot into a graph.

        Arguments:
        Any accepted by GCBMResultsProvider and subclasses.

        Returns a list of Frames, one for each year of output.
        '''
        indicator_data = self._provider.get_annual_result(start_year, end_year, self._units, **kwargs)
        years = sorted(indicator_data)
        values = [indicator_data[year] for year in years]

        frames = []
        for i, year in enumerate(years):
            with self._figure(figsize=(10, 5)) as fig:
                y_label = f"{self._title} ({self._units.value[2]})"
                plt.xlabel("Years", fontweight="bold", fontsize=14)
                plt.ylabel(y_label, fontweight="bold", fontsize=14)
                plt.axhline(0, color="darkgray")
                plt.plot(years, values, marker="o", linestyle="--", color="navy")
                
                # Mark the current year.
                plt.plot(year, indicator_data[year], marker="o", linestyle="--", color="b", markersize=15)

                plt.axis([None, None, min(values) - 0.1, max(values) + 0.1])
                plt.tick_params(axis="both", labelsize=14)
                plt.xticks(fontsize=12, fontweight="bold")
                plt.yticks(fontsize=12, fontweight="bold")

                # Remove scientific notation.
                ax = plt.gca()
                ax.get_yaxis().get_major_formatter().set_useOffset(False)

                # Add a vertical line at the current year.
                pos = year - 0.2 if i == len(years) - 1 else year + 0.2
                plt.axvspan(year, pos, facecolor="g", alpha=0.5)

                # Shade underneath the value series behind the current year.
                shaded_years = np.array(years)
                shaded_values = np.array(values).copy()
                shaded_values[shaded_years > year] = np.nan
                plt.fill_between(shaded_years, shaded_values, facecolor="gainsboro")

                out_file = TempFileManager.mktmp(suffix=".png")
                fig.savefig(out_file, bbox_inches="tight", dpi=300)
                frames.append(Frame(year, out_file))

        return frames

    @contextmanager
    def _figure(self, *args, **kwargs):
        fig = plt.figure(*args, **kwargs)
        try:
            yield fig
        finally:
            plt.close(fig)
            plt.clf()
