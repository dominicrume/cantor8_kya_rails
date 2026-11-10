I measured how a Canton Dev Fund proposal actually reaches a vote.

Seven votes have failed. Six recorded no vote against at all. They failed
because eligible voters did not vote, and under a 51%-of-allowed-voters
threshold an absence is a no.

Four of the seven were re-opened within four days, so a failed vote is a
restarted clock rather than a verdict.

The part worth your time: `gh pr list --label gitvote/failed` returns three,
not seven. A re-opened vote has its label reset, so the obvious measurement
is wrong by four and nothing in its output says so. My own tool counted that
way until today.

Method, tool and every number, re-runnable:
https://github.com/dominicrume/cantor8_kya_rails/blob/main/docs/dev-fund-vote-mechanism.md

@CantonFdn #CantonResearchNov26
