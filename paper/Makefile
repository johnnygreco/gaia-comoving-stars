LATEX       = pdflatex -interaction=nonstopmode -halt-on-error
BASH        = bash -c
ECHO        = echo
RM          = rm -rf
TMP_SUFFS   = pdf aux bbl blg log dvi ps eps out brf
CHECK_RERUN =

NAME = ms

all: ${NAME}.pdf

gitstuff.tex: ../.git/logs/HEAD
	echo "%%% This file is generated by the Makefile." > gitstuff.tex
	git log -1 --date=short --format="format:\\newcommand{\\githash}{%h}\\newcommand{\\gitdate}{%ad}\\newcommand{\\gitauthor}{%an}" >> gitstuff.tex

${NAME}.pdf: ${NAME}.tex *.bib gitstuff.tex aastexmods.tex
	${LATEX} ${NAME}
	bibtex ${NAME}
	${LATEX} ${NAME}
	( grep "Rerun to get" ${NAME}.log && ${LATEX} ${NAME} ) || echo "Done."
	( grep "Rerun to get" ${NAME}.log && ${LATEX} ${NAME} ) || echo "Done."

clean:
	${RM} $(foreach suff, ${TMP_SUFFS}, ${NAME}.${suff})
	${RM} aastexmods.aux
	${RM} gitstuff.aux
	${RM} *Notes.bib

submit: ${NAME}.pdf
	make
	tar -czvf archive.tar.gz $$(git ls-tree --name-only HEAD | grep -v ".gitignore\|Makefile\|figures") -C ./figures/ $$(cd figures && git ls-files)
	echo "archive.tar.gz created"

