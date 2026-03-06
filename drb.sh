#!/bin/sh
# drb: Read the Douay-Rheims Bible from your terminal
# License: Public domain

SELF="$0"

get_data() {
	sed '1,/^#EOF$/d' < "$SELF" | tar xzf - -O "$1"
}

get_text_data() {
	case "${DRB_TRANSLATION:-challoner}" in
		1609) get_data drb-1609.tsv ;;
		*)    get_data drb.tsv ;;
	esac
}

if [ -z "$PAGER" ]; then
	if command -v less >/dev/null; then
		PAGER="less"
	else
		PAGER="cat"
	fi
fi

show_help() {
	exec >&2
	echo "usage: $(basename "$0") [flags] [reference...]"
	echo
	echo "  -l              list books"
	echo "  -r              random verse"
	echo "  -t [VERSION]    translation version (default: challoner)"
	echo "                  versions: challoner, 1609"
	echo "  -c [SOURCE]     show commentary (default: haydock)"
	echo "                  sources: haydock, lapide, douai, aquinas, chrysostom"
	echo "                  Note: douai (alias: 1609) uses original 1609 spelling —"
	echo "                  ſ rendered as f, archaic orthography is authentic"
	echo "                  aquinas: Catena Aurea (Gospels) + Epistles commentary"
	echo "  -W              no line wrap"
	echo "  -h              show help"
	echo
	echo "  Reference types:"
	echo "      <Book>"
	echo "          Individual book"
	echo "      <Book>:<Chapter>"
	echo "          Individual chapter of a book"
	echo "      <Book>:<Chapter>:<Verse>[,<Verse>]..."
	echo "          Individual verse(s) of a specific chapter of a book"
	echo "      <Book>:<Chapter>-<Chapter>"
	echo "          Range of chapters in a book"
	echo "      <Book>:<Chapter>:<Verse>-<Verse>"
	echo "          Range of verses in a book chapter"
	echo "      <Book>:<Chapter>:<Verse>-<Chapter>:<Verse>"
	echo "          Range of chapters and verses in a book"
	echo
	echo "      /<Search>"
	echo "          All verses that match a pattern"
	echo "      <Book>/<Search>"
	echo "          All verses in a book that match a pattern"
	echo "      <Book>:<Chapter>/<Search>"
	echo "          All verses in a chapter of a book that match a pattern"
	exit 2
}

while [ $# -gt 0 ]; do
	isFlag=0
	firstChar="${1%"${1#?}"}"
	if [ "$firstChar" = "-" ]; then
		isFlag=1
	fi

	if [ "$1" = "--" ]; then
		shift
		break
	elif [ "$1" = "-l" ]; then
		get_text_data | awk -v cmd=list "$(get_data drb.awk)"
		exit
	elif [ "$1" = "-r" ]; then
		total=$(get_text_data | wc -l)
		line=$(awk 'BEGIN{srand(); print int(rand()*'"$total"')+1}')
		get_text_data | awk -v cmd=random -v line="$line" "$(get_data drb.awk)"
		exit
	elif [ "$1" = "-c" ]; then
		shift
		case "$1" in
			haydock|lapide|douai|1609|aquinas|chrysostom|all)
				if [ -z "$DRB_COMMENTARY" ]; then
					export DRB_COMMENTARY="$1"
				else
					export DRB_COMMENTARY="${DRB_COMMENTARY},$1"
				fi
				shift
				;;
			-*|"")
				if [ -z "$DRB_COMMENTARY" ]; then
					export DRB_COMMENTARY="haydock"
				else
					export DRB_COMMENTARY="${DRB_COMMENTARY},haydock"
				fi
				;;
			*)
				# Not a known source, might be a book reference — default to haydock
				if [ -z "$DRB_COMMENTARY" ]; then
					export DRB_COMMENTARY="haydock"
				else
					export DRB_COMMENTARY="${DRB_COMMENTARY},haydock"
				fi
				;;
		esac
	elif [ "$1" = "-t" ]; then
		shift
		case "$1" in
			challoner|1609)
				export DRB_TRANSLATION="$1"
				shift
				;;
			-*|"")
				export DRB_TRANSLATION="challoner"
				;;
			*)
				export DRB_TRANSLATION="challoner"
				;;
		esac
	elif [ "$1" = "-W" ]; then
		export DRB_NOLINEWRAP=1
		shift
	elif [ "$1" = "-h" ] || [ "$isFlag" -eq 1 ]; then
		show_help
	else
		break
	fi
done

if cols=$(tput cols 2>/dev/null); then
	export DRB_MAX_WIDTH="$cols"
fi

if [ $# -eq 0 ]; then
	if [ ! -t 0 ]; then
		show_help
	fi

	while true; do
		printf "drb> "
		if ! read -r ref; then
			break
		fi
		get_text_data | awk -v cmd=ref -v ref="$ref" "$(get_data drb.awk)" | ${PAGER}
	done
	exit 0
fi

(
get_text_data | awk -v cmd=ref -v ref="$*" "$(get_data drb.awk)"
if [ -n "${DRB_COMMENTARY}" ]; then
	# Map full book names to Lapide abbreviations
	lapide_abbrev() {
		case "$1" in
			# Old Testament
			Genesis) echo "Gn" ;; Exodus) echo "Ex" ;; Leviticus) echo "Lv" ;;
			Numbers) echo "Nm" ;; Deuteronomy) echo "Dt" ;; Joshua) echo "Jos" ;;
			Judges) echo "Jgs" ;; Ruth) echo "Ru" ;;
			"1 Samuel") echo "1Sm" ;; "2 Samuel") echo "2Sm" ;;
			"1 Kings") echo "1Kgs" ;; "2 Kings") echo "2Kgs" ;;
			"1 Chronicles") echo "1Chr" ;; "2 Chronicles") echo "2Chr" ;;
			Ezra) echo "Ezr" ;; Nehemiah) echo "Neh" ;;
			Tobit) echo "Tb" ;; Judith) echo "Jdt" ;; Esther) echo "Est" ;;
			"1 Maccabees") echo "1Mc" ;; "2 Maccabees") echo "2Mc" ;;
			Job) echo "Jb" ;; Psalms) echo "Ps" ;; Proverbs) echo "Prv" ;;
			Ecclesiastes) echo "Eccl" ;; "Song of Solomon") echo "Sg" ;;
			Wisdom) echo "Wis" ;; Sirach) echo "Sir" ;;
			Isaiah) echo "Is" ;; Jeremiah) echo "Jer" ;; Lamentations) echo "Lam" ;;
			Baruch) echo "Bar" ;; Ezekiel) echo "Ez" ;; Daniel) echo "Dn" ;;
			Hosea) echo "Hos" ;; Joel) echo "Jl" ;; Amos) echo "Am" ;;
			Obadiah) echo "Ob" ;; Jonah) echo "Jon" ;; Micah) echo "Mi" ;;
			Nahum) echo "Na" ;; Habakkuk) echo "Hb" ;; Zephaniah) echo "Zep" ;;
			Haggai) echo "Hg" ;; Zechariah) echo "Zec" ;; Malachi) echo "Mal" ;;
			# New Testament
			Matthew) echo "Mt" ;; Mark) echo "Mk" ;; Luke) echo "Lk" ;;
			John) echo "Jn" ;; "1 Corinthians") echo "1Cor" ;;
			"2 Corinthians") echo "2Cor" ;; Galatians) echo "Gal" ;;
			"1 John") echo "1Jn" ;; *) echo "" ;;
		esac
	}

	# Map full DRB book names to 1609 Douai TSV abbreviations
	douai_abbrev() {
		case "$1" in
			Genesis) echo "Gn" ;; Exodus) echo "Ex" ;; Leviticus) echo "Lv" ;;
			Numbers) echo "Nm" ;; Deuteronomy) echo "Dt" ;; Joshua) echo "Jos" ;;
			Judges) echo "Jgs" ;; Ruth) echo "Ru" ;; Ezra) echo "Ezr" ;;
			Tobit) echo "Tb" ;; Judith) echo "Jdt" ;; Esther) echo "Est" ;;
			"1 Maccabees") echo "1Mc" ;; Job) echo "Jb" ;; Psalms) echo "Ps" ;;
			Proverbs) echo "Prv" ;; Ecclesiastes) echo "Eccl" ;;
			"Song of Solomon") echo "Sg" ;; Wisdom) echo "Wis" ;;
			Sirach) echo "Sir" ;; Isaiah) echo "Is" ;; Jeremiah) echo "Jer" ;;
			Baruch) echo "Bar" ;; Daniel) echo "Dn" ;; Amos) echo "Am" ;;
			Zechariah) echo "Zec" ;; Malachi) echo "Mal" ;; Matthew) echo "Mt" ;;
			Mark) echo "Mk" ;; Luke) echo "Lk" ;; John) echo "Jn" ;;
			Romans) echo "Rom" ;; "1 Corinthians") echo "1Cor" ;;
			Galatians) echo "Gal" ;; Ephesians) echo "Eph" ;;
			Philippians) echo "Phil" ;; Colossians) echo "Col" ;;
			Hebrews) echo "Heb" ;; Titus) echo "Ti" ;; Philemon) echo "Phlm" ;;
			Jude) echo "Jude" ;; Apocalypse) echo "Apc" ;; *) echo "" ;;
		esac
	}

	# Map full DRB book names to Aquinas TSV abbreviations (Gospels + Pauline epistles + Job)
	aquinas_abbrev() {
		case "$1" in
			Matthew) echo "Mt" ;; Mark) echo "Mk" ;; Luke) echo "Lk" ;;
			John) echo "Jn" ;; Romans) echo "Rom" ;;
			"1 Corinthians") echo "1Cor" ;; "2 Corinthians") echo "2Cor" ;;
			Galatians) echo "Gal" ;; Ephesians) echo "Eph" ;;
			Philippians) echo "Phil" ;; Colossians) echo "Col" ;;
			"1 Thessalonians") echo "1Th" ;; "2 Thessalonians") echo "2Th" ;;
			"1 Timothy") echo "1Tim" ;; "2 Timothy") echo "2Tim" ;;
			Titus) echo "Ti" ;; Philemon) echo "Phlm" ;; Hebrews) echo "Heb" ;;
			Job) echo "Jb" ;;
			Psalms) echo "Ps" ;;
			Isaiah) echo "Is" ;;
			*) echo "" ;;
		esac
	}

	# Map full DRB book names to Chrysostom TSV abbreviations
	chrysostom_abbrev() {
		case "$1" in
			Matthew) echo "Mt" ;;
			John) echo "Jn" ;;
			Romans) echo "Rom" ;;
			"1 Corinthians") echo "1Cor" ;;
			*) echo "" ;;
		esac
	}

	# Expand "all" and build source list
	sources=""
	case "${DRB_COMMENTARY}" in
		*all*) sources="haydock lapide douai aquinas chrysostom" ;;
		*)
			IFS=','
			for s in ${DRB_COMMENTARY}; do
				case "$s" in
					haydock|lapide|douai|1609|aquinas|chrysostom) sources="$sources $s" ;;
				esac
			done
			unset IFS
			;;
	esac

	# Save reference for use inside function
	_ref="$*"

	show_commentary() {
		_src="$1"
		case "$_src" in
			haydock)    _label="Haydock Commentary"         ; _tsv="haydock.tsv" ;;
			lapide)     _label="Cornelius à Lapide"         ; _tsv="lapide.tsv" ;;
			douai|1609) _label="Douai Annotations (1609)"   ; _tsv="douai-1609.tsv" ;;
			aquinas)    _label="Aquinas (Catena Aurea)"      ; _tsv="" ;;
			chrysostom) _label="St. John Chrysostom"          ; _tsv="" ;;
		esac
		echo ""
		echo "--- ${_label} ---"
		echo ""
		get_text_data | awk -v cmd=ref -v ref="$_ref" "$(get_data drb.awk)" | \
		sed -n 's/^\([A-Za-z0-9 ]*\)$/BOOK:\1/p; s/^\([0-9]*:[0-9]*\)\t.*/\1/p' | \
		while IFS= read -r line; do
			case "$line" in
				BOOK:*) curbook="${line#BOOK:}" ;;
				*)
					if [ "$_src" = "lapide" ]; then
						abbrev=$(lapide_abbrev "$curbook")
						if [ -z "$abbrev" ]; then
							continue
						fi
						get_data "$_tsv" | grep "^${abbrev}	${line}	" | cut -f3 | \
						   awk -v verse="$line" 'BEGIN{printf "  %s\t", verse}{print}'
					elif [ "$_src" = "douai" ] || [ "$_src" = "1609" ]; then
						abbrev=$(douai_abbrev "$curbook")
						if [ -z "$abbrev" ]; then
							continue
						fi
						get_data "$_tsv" | grep "^${abbrev}	${line}	" | cut -f3 | \
						   awk -v verse="$line" 'BEGIN{printf "  %s\t", verse}{print}'
					elif [ "$_src" = "aquinas" ]; then
						abbrev=$(aquinas_abbrev "$curbook")
						if [ -z "$abbrev" ]; then
							continue
						fi
						case "$abbrev" in
							Mt|Mk|Lk|Jn) _aq_tsv="aquinas-catena.tsv" ;;
							Jb)           _aq_tsv="aquinas-job.tsv" ;;
							Ps)           _aq_tsv="aquinas-psalms.tsv" ;;
							Is)           _aq_tsv="aquinas-isaiah.tsv" ;;
							*)            _aq_tsv="aquinas-epistles.tsv" ;;
						esac
						# Aquinas TSVs use book/chapter/verse columns (not book/chapter:verse).
						# Commentary is in column 5. Use section-based lookup: find the section
						# whose start verse is nearest (≤ requested verse, or first in chapter).
						_aq_ch="${line%%:*}"
						_aq_vs="${line##*:}"
						get_data "$_aq_tsv" | awk -F'	' \
						   -v bk="$abbrev" -v ch="$_aq_ch" -v vs="$_aq_vs" -v vref="$line" \
						   'NR>1 && $1==bk && $2==ch {
						       if ($3+0<=vs+0) { nearest=$5 }
						       else if (nearest=="") { nearest=$5 }
						   }
						   END { if (nearest!="") printf "  %s\t%s\n", vref, nearest }'
					elif [ "$_src" = "chrysostom" ]; then
						abbrev=$(chrysostom_abbrev "$curbook")
						if [ -z "$abbrev" ]; then
							continue
						fi
						case "$abbrev" in
							Mt)       _ch_tsv="chrysostom-matthew.tsv" ;;
							Jn)       _ch_tsv="chrysostom-john.tsv" ;;
							Rom|1Cor) _ch_tsv="chrysostom-epistles.tsv" ;;
							*)        continue ;;
						esac
						# Chrysostom TSVs use 4 columns: book/chapter/verse/commentary.
						# Section-based lookup: find nearest verse ≤ requested.
						_ch_ch="${line%%:*}"
						_ch_vs="${line##*:}"
						get_data "$_ch_tsv" | awk -F'	' \
						   -v bk="$abbrev" -v ch="$_ch_ch" -v vs="$_ch_vs" -v vref="$line" \
						   'NR>1 && $1==bk && $2==ch {
						       if ($3+0<=vs+0) { nearest=$4 }
						       else if (nearest=="") { nearest=$4 }
						   }
						   END { if (nearest!="") printf "  %s\t%s\n", vref, nearest }'
					else
						get_data "$_tsv" | grep "^${curbook}	${line}	" | cut -f3 | \
						   awk -v verse="$line" 'BEGIN{printf "  %s\t", verse}{print}'
					fi
					;;
			esac
		done
	}

	for src in $sources; do
		show_commentary "$src"
	done
fi
) | ${PAGER}
