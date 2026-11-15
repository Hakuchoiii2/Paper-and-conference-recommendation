# Xác minh nguồn cho các ca bị flag

Thực hiện sau khi đã khóa lượt trích đầu. Tài liệu ngoài dùng để kiểm tra chất lượng nguồn, không được bổ sung sự kiện vắng mặt trong title/abstract vào nhãn đầu vào.

## P003168

Publisher full text section 5.1 explicitly identifies BioProp as the target-domain experimental dataset. Its role is not stated by the availability sentence alone in the supplied title/abstract. [Nguồn 1](https://academic.oup.com/bioinformatics/article/26/8/1098/205685).

Do not add PropBank or full-text facts absent from model input. Current conservative [] is a decision about abstract-only support, not a claim the paper did not use BioProp.

## P001234

The arXiv abstract itself spells the resource OpenStreatMap; the paper body section 2.4 identifies OpenStreetMap as the knowledge base. The local spelling is therefore not a local normalization error. [Nguồn 1](https://arxiv.org/abs/1601.05893), [Nguồn 2](https://arxiv.org/pdf/1601.05893).

Keep raw input and generated label OpenStreatMap. Record the externally confirmed spelling relation separately; do not silently correct model input or apply an unscoped matcher alias.

## P000271

The author-archive text contains the supplied paragraph at the beginning of the chapter, followed by details of an actual recurrent computer procedure absent from the supplied input. Coverage cannot be recovered solely by relabeling the given paragraph. [Nguồn 1](https://www.zelligharris.org/Papers%20in%20Structural%20and%20Transformational%20Linguistics.pdf).

Retain only source-supported labels. Full-text procedures/findings are not added to title/abstract labels. Input completeness remains a data-quality decision for a later source revision.

## P000779

The national-library catalog identifies a 1991 printed book of 335 pages from University Press of Virginia. Google Books shows the same descriptive summary as the local input. This supports the concern that the input is a book description rather than a conventional research-paper abstract. [Nguồn 1](https://catalogue.bnf.fr/ark%3A/12148/cb371608390), [Nguồn 2](https://books.google.com/books/about/Totalitarian_Language.html?id=Aop8QgAACAAJ).

Do not delete a v1 row or alter the held-out benchmark. Flag source-type and IT-scope eligibility for the next dataset version; current annotations describe only supplied text.

## P004191

The primary paper identifies its best hybrid model as the model evaluated on the independent dataset, with accuracy 0.80. This confirms the proposed A9+A10 antecedent rather than assigning the score to a dataset or every hybrid model. [Nguồn 1](https://pubmed.ncbi.nlm.nih.gov/19358699/), [Nguồn 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC2676257/).

Retain the multi-sentence finding using only source words from A9/A10. Do not add the server/model name, miRBase or other details available only in full text.
